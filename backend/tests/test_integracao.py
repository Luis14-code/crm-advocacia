"""Testes de integração dos fluxos críticos (requerem banco + seed; rode no container)."""
import uuid

from tests.conftest import SEED_SOCIO


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_login_e_me(client, token_socio):
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_socio}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == SEED_SOCIO["email"]
    assert resp.json()["perfil"] == "socio"


async def test_login_invalido(client):
    resp = await client.post("/api/auth/login", json={"email": "nao@existe.test", "senha": "x"})
    assert resp.status_code == 401


async def test_token_invalido_401(client):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert resp.status_code == 401


async def test_crud_cliente(client, token_socio):
    h = {"Authorization": f"Bearer {token_socio}"}
    cpf = f"{uuid.uuid4().int % 10**11:011d}"
    resp = await client.post("/api/clientes", headers=h, json={"nome": "Fulano Teste", "cpf": cpf})
    assert resp.status_code == 201, resp.text
    cid = resp.json()["id"]
    resp = await client.get("/api/clientes?busca=Fulano", headers=h)
    assert resp.status_code == 200
    assert any(c["id"] == cid for c in resp.json())
    resp = await client.get(f"/api/clientes/{cid}", headers=h)
    assert resp.status_code == 200
    resp = await client.delete(f"/api/clientes/{cid}", headers=h)
    assert resp.status_code == 204


async def test_financeiro_exige_token_sensivel(client, token_socio):
    h = {"Authorization": f"Bearer {token_socio}"}
    resp = await client.get("/api/financeiro/transacoes", headers=h)
    assert resp.status_code == 403


async def test_dono_exige_token_sensivel(client, token_socio):
    h = {"Authorization": f"Bearer {token_socio}"}
    resp = await client.get("/api/dono/dashboard", headers=h)
    assert resp.status_code == 403


async def test_verify_sensitive_e_financeiro(client, token_socio):
    """Com a senha sensível correta, o financeiro libera."""
    h = {"Authorization": f"Bearer {token_socio}"}
    resp = await client.post("/api/auth/verify-sensitive", headers=h, json={"senha_sensivel": "financeiro123"})
    assert resp.status_code == 200, resp.text
    st = resp.json()["sensitive_token"]
    resp = await client.get("/api/financeiro/transacoes", headers={**h, "X-Sensitive-Token": st})
    assert resp.status_code == 200


async def test_mural_acessivel(client, token_socio):
    h = {"Authorization": f"Bearer {token_socio}"}
    resp = await client.get("/api/mural", headers=h)
    assert resp.status_code == 200
    assert "eventos" in resp.json()
