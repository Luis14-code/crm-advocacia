"""Rotas de autenticação: login, refresh, verify-sensitive, me."""
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    criar_sensitive_token,
    decodificar_token,
    verificar_senha,
    verificar_senha_sensivel,
)
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    SensitiveRequest,
    SensitiveResponse,
    TokenResponse,
)
from app.schemas.usuario import UsuarioOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == body.email))
    usuario = result.scalar_one_or_none()
    if not usuario or not verificar_senha(body.senha, usuario.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    if not usuario.ativo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuário inativo")

    return TokenResponse(
        access_token=criar_access_token(usuario.id, usuario.perfil),
        refresh_token=criar_refresh_token(usuario.id),
        user=UsuarioOut.model_validate(usuario),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decodificar_token(body.refresh_token, "refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido")

    usuario = await db.get(Usuario, int(payload["sub"]))
    if not usuario or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inválido")
    return AccessTokenResponse(access_token=criar_access_token(usuario.id, usuario.perfil))


@router.post("/verify-sensitive", response_model=SensitiveResponse)
async def verify_sensitive(
    body: SensitiveRequest, user: Usuario = Depends(get_current_user)
):
    if not verificar_senha_sensivel(body.senha_sensivel):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha sensível incorreta")
    return SensitiveResponse(sensitive_token=criar_sensitive_token(user.id))


@router.get("/me", response_model=UsuarioOut)
async def me(user: Usuario = Depends(get_current_user)):
    return UsuarioOut.model_validate(user)
