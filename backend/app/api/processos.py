"""CRUD de processos com filtro de escopo por perfil."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models.enums import Perfil
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.processo import ProcessoCreate, ProcessoOut, ProcessoUpdate

router = APIRouter(prefix="/api/processos", tags=["processos"])

_pode_editar = require_roles(Perfil.socio, Perfil.advogado)


def _aplica_escopo(stmt, user: Usuario):
    """Advogado/estagiário só enxergam os próprios processos; sócio vê tudo."""
    if user.perfil in (Perfil.advogado.value, Perfil.estagiario.value):
        stmt = stmt.where(Processo.advogado_id == user.id)
    return stmt


@router.get("", response_model=list[ProcessoOut])
async def listar(
    status_: str | None = Query(default=None, alias="status"),
    advogado_id: int | None = None,
    busca: str | None = Query(default=None, description="Número ou tese"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    stmt = select(Processo)
    stmt = _aplica_escopo(stmt, user)
    if status_:
        stmt = stmt.where(Processo.status == status_)
    if advogado_id and user.perfil == Perfil.socio.value:
        stmt = stmt.where(Processo.advogado_id == advogado_id)
    if busca:
        termo = f"%{busca}%"
        stmt = stmt.where(Processo.numero.ilike(termo) | Processo.tese_principal.ilike(termo))
    stmt = stmt.order_by(Processo.updated_at.desc()).limit(limit).offset(offset)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{processo_id}", response_model=ProcessoOut)
async def obter(
    processo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    processo = await db.get(Processo, processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    if user.perfil in (Perfil.advogado.value, Perfil.estagiario.value) and processo.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este processo")
    return processo


@router.post("", response_model=ProcessoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: ProcessoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(_pode_editar),
):
    existe = await db.execute(select(Processo).where(Processo.numero == body.numero))
    if existe.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Número de processo já cadastrado")
    dados = body.model_dump()
    # Advogado só cria processo para si mesmo
    if user.perfil == Perfil.advogado.value:
        dados["advogado_id"] = user.id
    processo = Processo(**dados)
    db.add(processo)
    await db.flush()
    await db.refresh(processo)
    return processo


@router.put("/{processo_id}", response_model=ProcessoOut)
async def atualizar(
    processo_id: int,
    body: ProcessoUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(_pode_editar),
):
    processo = await db.get(Processo, processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    if user.perfil == Perfil.advogado.value and processo.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este processo")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(processo, campo, valor)
    await db.flush()
    await db.refresh(processo)
    return processo


@router.delete("/{processo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover(
    processo_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_roles(Perfil.socio)),
):
    processo = await db.get(Processo, processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    await db.delete(processo)
