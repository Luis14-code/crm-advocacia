"""CRUD de clientes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models.cliente import Cliente
from app.models.enums import Perfil
from app.models.usuario import Usuario
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate

router = APIRouter(prefix="/api/clientes", tags=["clientes"])

_pode_editar = require_roles(Perfil.socio, Perfil.advogado, Perfil.financeiro)


@router.get("", response_model=list[ClienteOut])
async def listar(
    busca: str | None = Query(default=None, description="Nome ou CPF"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = select(Cliente)
    if busca:
        termo = f"%{busca}%"
        stmt = stmt.where(or_(Cliente.nome.ilike(termo), Cliente.cpf.ilike(termo)))
    stmt = stmt.order_by(Cliente.nome).limit(limit).offset(offset)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{cliente_id}", response_model=ClienteOut)
async def obter(
    cliente_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    return cliente


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: ClienteCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_pode_editar),
):
    if body.cpf:
        existe = await db.execute(select(Cliente).where(Cliente.cpf == body.cpf))
        if existe.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "CPF já cadastrado")
    cliente = Cliente(**body.model_dump())
    db.add(cliente)
    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
async def atualizar(
    cliente_id: int,
    body: ClienteUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_pode_editar),
):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover(
    cliente_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_roles(Perfil.socio)),
):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    await db.delete(cliente)
