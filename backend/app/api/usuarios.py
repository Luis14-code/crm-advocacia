"""CRUD de usuários (restrito ao sócio)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.security import hash_senha
from app.database import get_db
from app.models.enums import Perfil
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

_socio = require_roles(Perfil.socio)


@router.get("", response_model=list[UsuarioOut])
async def listar(
    ativo: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_socio),
):
    stmt = select(Usuario)
    if ativo is not None:
        stmt = stmt.where(Usuario.ativo == ativo)
    return (await db.execute(stmt.order_by(Usuario.nome))).scalars().all()


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_socio),
):
    existe = await db.execute(select(Usuario).where(Usuario.email == body.email))
    if existe.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")
    dados = body.model_dump(exclude={"senha"})
    dados["perfil"] = body.perfil.value
    usuario = Usuario(**dados, senha_hash=hash_senha(body.senha))
    db.add(usuario)
    await db.flush()
    await db.refresh(usuario)
    return usuario


@router.put("/{usuario_id}", response_model=UsuarioOut)
async def atualizar(
    usuario_id: int,
    body: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_socio),
):
    usuario = await db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
    dados = body.model_dump(exclude_unset=True)
    if "senha" in dados:
        usuario.senha_hash = hash_senha(dados.pop("senha"))
    if "perfil" in dados and dados["perfil"] is not None:
        dados["perfil"] = dados["perfil"].value
    for campo, valor in dados.items():
        setattr(usuario, campo, valor)
    await db.flush()
    await db.refresh(usuario)
    return usuario
