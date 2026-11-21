"""Dependências compartilhadas: usuário atual, exigência de perfil e token sensível."""
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decodificar_token
from app.database import get_db
from app.models.enums import Perfil
from app.models.usuario import Usuario

bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    try:
        payload = decodificar_token(cred.credentials, "access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    usuario = await db.get(Usuario, int(payload["sub"]))
    if not usuario or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inativo ou inexistente")
    return usuario


def require_roles(*perfis: Perfil):
    """Fábrica de dependência que exige que o usuário tenha um dos perfis."""
    permitidos = {p.value for p in perfis}

    async def _checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.perfil not in permitidos:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Perfil '{user.perfil}' sem acesso a este recurso",
            )
        return user

    return _checker


async def require_sensitive(
    user: Usuario = Depends(get_current_user),
    x_sensitive_token: str | None = Header(default=None),
) -> Usuario:
    """Exige um sensitive_token válido (módulos financeiro / dashboard dono)."""
    if not x_sensitive_token:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Token sensível ausente (header X-Sensitive-Token)"
        )
    try:
        payload = decodificar_token(x_sensitive_token, "sensitive")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token sensível expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token sensível inválido")
    if int(payload["sub"]) != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token sensível de outro usuário")
    return user
