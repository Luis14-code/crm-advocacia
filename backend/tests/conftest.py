"""Fixtures para testes de integração.

Usam o app via ASGI e as credenciais do seed. Rode dentro do container:
`docker compose exec backend pytest`. Se o banco/seed não estiver disponível,
os testes que dependem dele são pulados.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import engine
from app.main import app

SEED_SOCIO = {"email": "socio@claudio.local", "senha": "claudio123"}


@pytest_asyncio.fixture(autouse=True)
async def _reset_engine():
    """Evita reuso do pool entre loops de teste (asyncpg é sensível a isso)."""
    await engine.dispose()
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def token_socio(client):
    resp = await client.post("/api/auth/login", json=SEED_SOCIO)
    if resp.status_code != 200:
        pytest.skip("Seed não aplicado (rode: docker compose exec backend python seed.py)")
    return resp.json()["access_token"]
