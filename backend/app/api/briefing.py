"""Briefing do dia (gerado sob demanda)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models.enums import Perfil
from app.models.usuario import Usuario
from app.services import briefing as svc

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.get("")
async def meu_briefing(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    return await svc.gerar_briefing(db, user.id)


@router.get("/{advogado_id}")
async def briefing_de(
    advogado_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_roles(Perfil.socio)),
):
    return await svc.gerar_briefing(db, advogado_id)
