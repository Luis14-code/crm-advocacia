"""Testes de integração dos fluxos críticos (requerem banco; rode no container)."""
import uuid


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_login_e_me(client, socio, token_socio):
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_socio}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == socio["email"]
    assert resp.json()["perfil"] == "socio"


async def test_login_invalido(client):
    resp = await client.post("/api/auth/login", json={"email": "nao@existe.test", "senha": "x"})
    assert resp.status_code == 401


async def test_token_expirado_ou_invalido_401(client):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert resp.status_code == 401


async def test_crud_cliente(client, token_socio):
    h = {"Authorization": f"Bearer {token_socio}"}
    cpf = f"{uuid.uuid4().int % 10**11:011d}"
    # criar
    resp = await client.post("/api/clientes", headers=h, json={"nome": "Fulano Teste", "cpf": cpf})
    assert resp.status_code == 201, resp.text
    cid = resp.json()["id"]
    # listar com busca
    resp = await client.get("/api/clientes?busca=Fulano", headers=h)
    assert resp.status_code == 200
    assert any(c["id"] == cid for c in resp.json())
    # obter
    resp = await client.get(f"/api/clientes/{cid}", headers=h)
    assert resp.status_code == 200
    # remover (limpeza)
    resp = await client.delete(f"/api/clientes/{cid}", headers=h)
    assert resp.status_code == 204


async def test_financeiro_exige_token_sensivel(client, token_socio):
    """Rota financeira retorna 403 sem o token sensível."""
    h = {"Authorization": f"Bearer {token_socio}"}
    resp = await client.get("/api/financeiro/transacoes", headers=h)
    assert resp.status_code == 403


async def test_dono_exige_token_sensivel(client, token_socio):
    h = {"Authorization": f"Bearer {token_socio}"}
    resp = await client.get("/api/dono/dashboard", headers=h)
    assert resp.status_code == 403


async def test_mural_acessivel(client, token_socio):
    h = {"Authorization": f"Bearer {token_socio}"}
    resp = await client.get("/api/mural", headers=h)
    assert resp.status_code == 200
    assert "eventos" in resp.json()
