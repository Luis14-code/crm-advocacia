"""CRUD/consulta de prazos com cálculo em dias úteis."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models.enums import Perfil
from app.models.prazo import Prazo
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.prazo import PrazoCreate, PrazoOut, PrazoUpdate
from app.services import prazos as sp

router = APIRouter(prefix="/api/prazos", tags=["prazos"])


@router.get("", response_model=list[PrazoOut])
async def listar(
    status_: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    stmt = select(Prazo).join(Processo, Prazo.processo_id == Processo.id)
    if user.perfil in (Perfil.advogado.value, Perfil.estagiario.value):
        stmt = stmt.where(Processo.advogado_id == user.id)
    if status_:
        stmt = stmt.where(Prazo.status == status_)
    stmt = stmt.order_by(Prazo.data_limite_util)
    return (await db.execute(stmt)).scalars().all()


@router.post("", response_model=PrazoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: PrazoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(require_roles(Perfil.socio, Perfil.advogado)),
):
    processo = await db.get(Processo, body.processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    if user.perfil == Perfil.advogado.value and processo.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este processo")

    # Se vierem dias úteis, calcula a data-limite a partir de hoje; senão usa a data informada.
    if body.dias_uteis is not None:
        data_limite = sp.adicionar_dias_uteis(date.today(), body.dias_uteis)
    else:
        data_limite = body.data_limite

    prazo = Prazo(
        processo_id=body.processo_id,
        responsavel_id=body.responsavel_id or processo.advogado_id,
        descricao=body.descricao,
        data_limite=data_limite,
        data_limite_util=sp.data_limite_util(data_limite),
    )
    db.add(prazo)
    await db.flush()
    await db.refresh(prazo)
    return prazo


@router.patch("/{prazo_id}", response_model=PrazoOut)
async def atualizar(
    prazo_id: int,
    body: PrazoUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(require_roles(Perfil.socio, Perfil.advogado)),
):
    prazo = await db.get(Prazo, prazo_id)
    if not prazo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prazo não encontrado")
    dados = body.model_dump(exclude_unset=True)
    if "data_limite" in dados and dados["data_limite"]:
        prazo.data_limite = dados["data_limite"]
        prazo.data_limite_util = sp.data_limite_util(dados["data_limite"])
    if "status" in dados and dados["status"]:
        prazo.status = dados["status"]
    if "descricao" in dados and dados["descricao"]:
        prazo.descricao = dados["descricao"]
    await db.flush()
    await db.refresh(prazo)
    return prazo
