"""Endpoints da 'Análise do dia' (análise aprofundada por processo + plano de ação).

- GET  /api/analise/dia         → analisa (somente leitura; pode chamar à vontade).
- POST /api/analise/dia/processar → grava as mensagens na fila de pré-aprovação e
                                     marca a análise como vista.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.enums import Perfil
from app.models.usuario import Usuario
from app.services import analise

router = APIRouter(prefix="/api/analise", tags=["analise"])


def _alvo(user: Usuario, advogado_id: int | None) -> int:
    """Advogado olha a própria análise; sócio pode olhar a de qualquer um."""
    if advogado_id and advogado_id != user.id and user.perfil != Perfil.socio.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso à análise de outro advogado")
    return advogado_id or user.id


@router.get("/dia")
async def analise_dia(
    advogado_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    return await analise.analise_do_dia(db, _alvo(user, advogado_id), criar_rascunhos=False)


@router.post("/dia/processar")
async def processar_dia(
    advogado_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    alvo = _alvo(user, advogado_id)
    resultado = await analise.analise_do_dia(db, alvo, criar_rascunhos=True)
    await analise.marcar_visto(db, alvo, quando=datetime.fromisoformat(resultado["gerado_em"]))
    return resultado
