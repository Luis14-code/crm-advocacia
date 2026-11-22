"""Dashboard do Dono — exige perfil sócio + token sensível."""
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_sensitive
from app.core.cache import cached_json, invalidar
from app.database import get_db
from app.models.enums import Perfil
from app.models.usuario import Usuario
from app.services import configuracoes as cfg
from app.services import dono, jurimetria

router = APIRouter(prefix="/api/dono", tags=["dono"])


async def acesso_dono(user: Usuario = Depends(require_sensitive)) -> Usuario:
    if user.perfil != Perfil.socio.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso exclusivo do sócio")
    return user


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(acesso_dono)
):
    return await cached_json("dono:dashboard", 60, lambda: dono.dashboard(db))


@router.get("/jurimetria")
async def jurimetria_endpoint(
    dimensao: str = Query(default="tese", pattern="^(tese|juiz|vara|tipo)$"),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_dono),
):
    return await cached_json(
        f"dono:jurimetria:{dimensao}", 120, lambda: jurimetria.taxa_exito_por(db, dimensao)
    )


@router.get("/advogados")
async def advogados(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(acesso_dono)
):
    return await cached_json("dono:advogados", 60, lambda: jurimetria.comparar_advogados(db))


@router.get("/advogado/{advogado_id}")
async def relatorio(
    advogado_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_dono),
):
    return await jurimetria.relatorio_detalhado(db, advogado_id)


@router.get("/meta")
async def obter_meta(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(acesso_dono)
):
    return {"meta_faturamento_mensal": await cfg.get_meta_faturamento(db)}


@router.put("/meta")
async def definir_meta(
    valor: float = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_dono),
):
    await cfg.definir(db, cfg.META_FATURAMENTO, str(valor), descricao="Meta de faturamento mensal")
    await db.flush()
    await invalidar("dono:")  # invalida o cache do dashboard
    return {"meta_faturamento_mensal": valor}
