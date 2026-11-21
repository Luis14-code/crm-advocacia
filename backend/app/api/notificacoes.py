"""Notificações internas (badge do header)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.notificacao import Notificacao
from app.models.usuario import Usuario
from app.schemas.notificacao import NotificacaoOut

router = APIRouter(prefix="/api/notificacoes", tags=["notificacoes"])


@router.get("", response_model=list[NotificacaoOut])
async def listar(
    apenas_nao_lidas: bool = Query(default=False),
    limit: int = Query(default=30, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    stmt = select(Notificacao).where(Notificacao.usuario_id == user.id)
    if apenas_nao_lidas:
        stmt = stmt.where(Notificacao.lida.is_(False))
    stmt = stmt.order_by(Notificacao.created_at.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


@router.get("/unread-count")
async def nao_lidas(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    total = (
        await db.execute(
            select(func.count())
            .select_from(Notificacao)
            .where(Notificacao.usuario_id == user.id, Notificacao.lida.is_(False))
        )
    ).scalar_one()
    return {"unread": total}


@router.post("/{notificacao_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def marcar_lida(
    notificacao_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    notif = await db.get(Notificacao, notificacao_id)
    if not notif or notif.usuario_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificação não encontrada")
    notif.lida = True


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def marcar_todas(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    await db.execute(
        update(Notificacao)
        .where(Notificacao.usuario_id == user.id, Notificacao.lida.is_(False))
        .values(lida=True)
    )
