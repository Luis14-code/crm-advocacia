# Cláudio — CRM Jurídico com Agente de IA

Plataforma CRM **local** para escritórios de advocacia (foco previdenciário), com um
agente conversacional (Cláudio) integrado. Roda 100% na máquina do escritório via Docker.

> **Status:** Fase 1 — Fundação (infra + auth + CRUD + agente com 3 plugins).

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11 · FastAPI (async + WebSocket) |
| Frontend | React 18 · Vite · TailwindCSS |
| Banco | PostgreSQL 16 + pgvector |
| Fila/Cache | Celery · Redis |
| LLM | Ollama (opcional na Fase 1) |
| Proxy | Caddy (produção) |

## Pré-requisitos

- Docker + Docker Compose
- (Opcional) GPU NVIDIA para Ollama/Whisper nas próximas fases

## Como rodar (desenvolvimento)

```bash
# 1. Configurar ambiente
cp .env.example .env
# Gere as chaves e preencha no .env:
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print('FERNET_KEY=' + Fernet.generate_key().decode())"
python -c "import bcrypt; print('SENSITIVE_PASSWORD_HASH=' + bcrypt.hashpw(b'senha-financeiro', bcrypt.gensalt(12)).decode())"

# 2. Subir os serviços (db, redis, backend, worker, frontend)
docker compose --profile dev up -d --build

# 3. As migrations rodam automaticamente no boot do backend.
#    Popular dados iniciais:
docker compose exec backend python seed.py
```

Acesse:
- Frontend: http://localhost:5173
- API (docs): http://localhost:8000/docs
- Health: http://localhost:8000/api/health

### Usuários de exemplo (após o seed)

| Perfil | E-mail | Senha |
|---|---|---|
| Sócio | `socio@claudio.local` | `claudio123` |
| Advogado | `advogado@claudio.local` | `claudio123` |

### Experimente o Cláudio

No chat (painel lateral), pergunte:
- "quais processos eu tenho?"
- "buscar cliente José"
- "ajuda"

> O agente usa o Ollama para classificar intenções quando disponível; sem o Ollama,
> cai num roteamento por palavras-chave, então os 3 plugins funcionam mesmo sem GPU.
> Para habilitar o LLM: `docker compose --profile dev --profile llm up -d` e
> `docker compose exec ollama ollama pull llama3.1:8b`.

## Produção

```bash
docker compose --profile prod up -d --build
```
O Caddy termina TLS e faz proxy de frontend/backend. Ajuste `DOMAIN` no `.env`.

## Testes

```bash
docker compose exec backend pytest
```

## Estrutura

```
backend/   FastAPI, modelos, auth, CRUD, agente (plugins), migrations
frontend/  React + Vite + Tailwind (login, layout, processos, chat)
scripts/   backup, utilidades
```

## Roadmap

- **Fase 1 ✅** Fundação: infra, auth, CRUD, agente (3 plugins)
- **Fase 2 ✅** Inteligência jurídica: DataJud/JusBrasil, briefing matinal, prazos
- **Fase 3 ✅** Reuniões (Whisper), RAG e geração de peças (PDF)
- **Fase 4 ✅** Financeiro (senha sensível), conciliação bancária e WhatsApp (WA-AKG)
- **Fase 5 ✅** Dashboard do dono, jurimetria, mural e aprendizado contínuo

Documentação: [RUNBOOK](docs/RUNBOOK.md) (operação) · [DEPLOY](docs/DEPLOY.md) (produção).

> Pós-roadmap (débitos técnicos): boleto com gateway real, Open Finance direto do banco,
> CI/CD, observabilidade (Loki/Grafana).
