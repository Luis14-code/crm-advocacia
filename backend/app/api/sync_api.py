"""Endpoints de sincronização: webhook do userscript JusBrasil e disparo manual."""
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.integrations import jusbrasil
from app.integrations.datajud import normalizar_numero
from app.models.enums import Perfil
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.services import sync

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/jusbrasil")
async def receber_jusbrasil(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Recebe movimentações extraídas pelo userscript (Tampermonkey) no Chrome do advogado."""
    dados = jusbrasil.normalizar_payload_userscript(payload)
    if not dados["numero"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Número do processo ausente")

    alvo = normalizar_numero(dados["numero"])
    processos = (await db.execute(select(Processo))).scalars().all()
    processo = next((p for p in processos if normalizar_numero(p.numero) == alvo), None)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não cadastrado")

    if user.perfil in (Perfil.advogado.value, Perfil.estagiario.value) and processo.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este processo")

    return await sync.sincronizar_movimentacoes_externas(
        db, processo, dados["movimentacoes"], fonte="jusbrasil"
    )


@router.post("/all")
async def sincronizar_tudo(
    _: Usuario = Depends(require_roles(Perfil.socio)),
):
    """Enfileira a sincronização de todos os processos ativos (task Celery)."""
    try:
        from app.tasks.sync_tasks import sync_processos

        task = sync_processos.delay()
        return {"status": "enfileirado", "task_id": task.id}
    except Exception as exc:  # noqa: BLE001  (broker indisponível)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Fila indisponível: {exc}",
        )
