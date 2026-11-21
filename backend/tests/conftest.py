"""Fixtures para testes de integração.

Os testes de integração usam o banco configurado em DATABASE_URL (rode dentro do
container: `docker compose exec backend pytest`). Se o banco não estiver acessível,
os testes que dependem dele são automaticamente pulados.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.security import hash_senha
from app.database import async_session_factory, engine
from app.main import app
from app.models.usuario import Usuario


async def _banco_acessivel() -> bool:
    try:
        async with engine.connect():
            return True
    except Exception:  # noqa: BLE001
        return False


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def socio():
    """Cria um sócio de teste, devolve (email, senha) e limpa ao final."""
    if not await _banco_acessivel():
        pytest.skip("Banco de dados indisponível para teste de integração")

    email = f"teste-{uuid.uuid4().hex[:8]}@claudio.test"
    senha = "senha-teste-123"
    async with async_session_factory() as db:
        u = Usuario(nome="Sócio Teste", email=email, senha_hash=hash_senha(senha), perfil="socio")
        db.add(u)
        await db.commit()
        uid = u.id

    yield {"email": email, "senha": senha, "id": uid}

    async with async_session_factory() as db:
        await db.execute(delete(Usuario).where(Usuario.id == uid))
        await db.commit()


@pytest_asyncio.fixture
async def token_socio(client, socio):
    resp = await client.post("/api/auth/login", json={"email": socio["email"], "senha": socio["senha"]})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
