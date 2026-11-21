"""Feedback do agente e registro de resultado de caso (jurimetria adaptativa)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models.agente import Feedback, ResultadoCaso
from app.models.enums import Perfil
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.aprendizado import FeedbackCreate, FeedbackOut, ResultadoCasoIn
from app.services import embeddings

router = APIRouter(prefix="/api", tags=["aprendizado"])


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def enviar_feedback(
    body: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    fb = Feedback(
        usuario_id=user.id,
        contexto=body.contexto,
        sugestao=body.sugestao,
        util=body.util,
        correcao=body.correcao,
    )
    db.add(fb)
    await db.flush()
    await db.refresh(fb)
    return fb


@router.post("/processos/{processo_id}/resultado")
async def registrar_resultado(
    processo_id: int,
    body: ResultadoCasoIn,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(require_roles(Perfil.socio, Perfil.advogado)),
):
    processo = await db.get(Processo, processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    if user.perfil == Perfil.advogado.value and processo.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este processo")

    existente = (
        await db.execute(select(ResultadoCaso).where(ResultadoCaso.processo_id == processo_id))
    ).scalar_one_or_none()

    dados = body.model_dump()
    dados["tese"] = dados.get("tese") or processo.tese_principal
    dados["juiz"] = dados.get("juiz") or processo.juiz
    dados["vara"] = dados.get("vara") or processo.vara

    if existente:
        for campo, valor in dados.items():
            setattr(existente, campo, valor)
        rc = existente
    else:
        rc = ResultadoCaso(processo_id=processo_id, **dados)
        db.add(rc)

    # Atualiza o processo
    processo.resultado = body.resultado
    processo.status = "encerrado"
    if not processo.data_encerramento:
        processo.data_encerramento = date.today()
    if body.valor_obtido is not None:
        processo.valor_resultado = body.valor_obtido

    await db.flush()

    # RAG: indexa o resultado (tese + estratégia + resultado)
    conteudo = " ".join(
        str(x) for x in [dados.get("tese"), dados.get("estrategia_usada"), body.resultado] if x
    )
    if conteudo.strip():
        await embeddings.indexar(
            db, "resultado", rc.id, conteudo,
            metadata={"tipo": processo.tipo, "resultado": body.resultado},
        )

    return {"status": "registrado", "resultado_id": rc.id}
