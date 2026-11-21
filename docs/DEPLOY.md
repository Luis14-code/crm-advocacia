# Deploy e Operação

Guia de produção. Para o passo a passo funcional (WhatsApp, banco, etc.), veja o
[RUNBOOK](RUNBOOK.md).

## Subir em produção

```bash
cp .env.example .env            # preencha JWT_SECRET, FERNET_KEY, SENSITIVE_PASSWORD_HASH, senhas
# ENVIRONMENT=production e DOMAIN=seu-dominio no .env
docker compose --profile prod up -d --build
```

Serviços do perfil `prod`: db (pgvector), redis, backend, worker (+beat),
whisper-worker, frontend (nginx) e caddy (TLS). Para WhatsApp/LLM, some os perfis:

```bash
docker compose --profile prod --profile whatsapp --profile llm up -d --build
```

- **Caddy** termina TLS automaticamente. Em rede local, usa certificado interno;
  com domínio público + DNS apontado, emite Let's Encrypt. Ajuste `DOMAIN` no `.env`.
- As **migrations** rodam no boot do backend (`alembic upgrade head`).

## Rede e segurança (já configurado)

- PostgreSQL, Redis e Ollama escutam apenas em `127.0.0.1` (não expostos).
- WA-AKG roda em rede interna do Compose; exponha só se precisar do painel.
- Senhas com bcrypt (cost 12); tokens de terceiros cifrados com Fernet.
- JWT: access 8h, refresh 7d; token sensível de 30min para financeiro/dono.
- CORS restrito às origens do `.env` (CORS_ORIGINS).
- Audit log imutável (apenas INSERT).

## Backup

```bash
# Manual
./scripts/backup.sh
# Agende no cron do host (ex.: 2h da manhã) — retenção via BACKUP_RETENTION_DAYS
0 2 * * *  /caminho/scripts/backup.sh
```
Restaurar: `gunzip -c backups/claudio_AAAA....sql.gz | docker compose exec -T db psql -U claudio claudio`.

## Workers e filas (Celery)

- `worker` (fila `celery` + beat): sync a cada 4h, briefing 7h, aprendizado a cada 2h.
- `whisper-worker` (fila `whisper`): transcrição de reuniões (isolada do LLM).
- Envios de WhatsApp são tasks com janela/rate limit; reagendam sozinhos.

## Hardware

- Mínimo (dev/CPU): 8 cores, 32 GB RAM. Whisper `tiny`, Ollama opcional.
- Recomendado (prod/GPU): 16 cores, 64 GB RAM, GPU ≥ 10 GB VRAM (LLM + Whisper).
- Sem GPU: tudo funciona, respostas de LLM/transcrição mais lentas.

## Performance

- Cache Redis nos endpoints pesados (dashboard do dono, jurimetria, mural).
- Índices criados nas migrations (prazos, movimentações, audit_log, embeddings ivfflat).
- Para bases grandes: considere particionar `movimentacoes` e `audit_log` após ~1M linhas.

## Testes

```bash
docker compose exec backend pytest        # unitários + integração (usa o banco)
```

## Observabilidade (débito técnico / próximos passos)

- Logs em stdout dos containers (`docker compose logs -f backend`).
- Futuro: centralização (Loki) e métricas (Prometheus/Grafana), CI/CD (GitHub Actions).
