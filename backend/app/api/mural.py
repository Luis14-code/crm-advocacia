"""Mural de conquistas — visível a todos os usuários autenticados (sem dados financeiros)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.cache import cached_json
from app.database import get_db
from app.models.usuario import Usuario
from app.services import mural as svc

router = APIRouter(prefix="/api/mural", tags=["mural"])


@router.get("")
async def feed(db: AsyncSession = Depends(get_db), _: Usuario = Depends(get_current_user)):
    return await cached_json("mural:feed", 30, lambda: svc.feed(db))
