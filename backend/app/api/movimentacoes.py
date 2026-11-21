"""Timeline de movimentações e sincronização manual de um processo."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models.enums import Perfil
from app.models.movimentacao import Movimentacao
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.movimentacao import MovimentacaoOut
from app.services import sync

router = APIRouter(prefix="/api/processos", tags=["movimentacoes"])


async def _processo_autorizado(db: AsyncSession, processo_id: int, user: Usuario) -> Processo:
    processo = await db.get(Processo, processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    if (
        user.perfil in (Perfil.advogado.value, Perfil.estagiario.value)
        and processo.advogado_id != user.id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este processo")
    return processo


@router.get("/{processo_id}/movimentacoes", response_model=list[MovimentacaoOut])
async def timeline(
    processo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    await _processo_autorizado(db, processo_id, user)
    movs = (
        await db.execute(
            select(Movimentacao)
            .where(Movimentacao.processo_id == processo_id)
            .order_by(Movimentacao.data.desc(), Movimentacao.id.desc())
        )
    ).scalars().all()
    return movs


@router.post("/{processo_id}/sync")
async def sincronizar(
    processo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(require_roles(Perfil.socio, Perfil.advogado)),
):
    processo = await _processo_autorizado(db, processo_id, user)
    resultado = await sync.sincronizar_processo(db, processo)
    return resultado
