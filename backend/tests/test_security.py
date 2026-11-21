"""Testes unitários mínimos de segurança (não exigem banco)."""
import jwt
import pytest

from app.core.security import (
    criar_access_token,
    criar_sensitive_token,
    decodificar_token,
    hash_senha,
    verificar_senha,
)


def test_hash_e_verificacao_de_senha():
    h = hash_senha("segredo123")
    assert h != "segredo123"
    assert verificar_senha("segredo123", h)
    assert not verificar_senha("errada", h)


def test_access_token_roundtrip():
    token = criar_access_token(usuario_id=7, perfil="advogado")
    payload = decodificar_token(token, "access")
    assert payload["sub"] == "7"
    assert payload["perfil"] == "advogado"
    assert payload["type"] == "access"


def test_tipo_de_token_incorreto_falha():
    token = criar_sensitive_token(usuario_id=1)
    with pytest.raises(jwt.InvalidTokenError):
        decodificar_token(token, "access")
