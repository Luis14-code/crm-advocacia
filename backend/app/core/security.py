"""Segurança: hashing de senha, JWT (access/refresh/sensitive) e Fernet."""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


# --- Senhas (bcrypt cost=12) ---
def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt(12)).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode(), senha_hash.encode())
    except (ValueError, TypeError):
        return False


# --- JWT ---
def _criar_token(dados: dict[str, Any], expira_em: timedelta, tipo: str) -> str:
    payload = dados.copy()
    now = datetime.now(timezone.utc)
    payload.update({"exp": now + expira_em, "iat": now, "type": tipo})
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def criar_access_token(usuario_id: int, perfil: str) -> str:
    return _criar_token(
        {"sub": str(usuario_id), "perfil": perfil},
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def criar_refresh_token(usuario_id: int) -> str:
    return _criar_token(
        {"sub": str(usuario_id)},
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def criar_sensitive_token(usuario_id: int) -> str:
    return _criar_token(
        {"sub": str(usuario_id)},
        timedelta(minutes=settings.sensitive_token_expire_minutes),
        "sensitive",
    )


def decodificar_token(token: str, tipo_esperado: str | None = None) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if tipo_esperado and payload.get("type") != tipo_esperado:
        raise jwt.InvalidTokenError(f"Esperado token do tipo '{tipo_esperado}'")
    return payload


# --- Senha sensível (módulos financeiro / dashboard dono) ---
def verificar_senha_sensivel(senha: str) -> bool:
    if not settings.sensitive_password_hash:
        return False
    return verificar_senha(senha, settings.sensitive_password_hash)


# --- Fernet (criptografia de tokens de terceiros) ---
def _fernet() -> Fernet | None:
    if not settings.fernet_key:
        return None
    return Fernet(settings.fernet_key.encode())


def criptografar(valor: str) -> str:
    f = _fernet()
    return f.encrypt(valor.encode()).decode() if f else valor


def descriptografar(valor: str) -> str | None:
    f = _fernet()
    if not f:
        return valor
    try:
        return f.decrypt(valor.encode()).decode()
    except InvalidToken:
        return None
