"""Aplicação FastAPI do Projeto Cláudio."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    analise_api,
    aprendizado,
    auth,
    briefing,
    chat_ws,
    clientes,
    config_api,
    documentos,
    dono,
    financeiro,
    movimentacoes,
    mural,
    notificacoes,
    pagamentos_api,
    prazos,
    processos,
    reunioes,
    sync_api,
    usuarios,
    whatsapp_api,
)
from app.config import settings

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Cláudio — CRM Jurídico",
    version="0.1.0",
    description="Plataforma CRM com agente de IA para escritórios de advocacia.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Libera também localhost e IPs de rede local (LAN) em qualquer porta, para o
    # acesso multiusuário de teste (outras máquinas abrindo pelo IP do servidor).
    allow_origin_regex=(
        r"^http://(localhost|127\.0\.0\.1"
        r"|10(\.\d{1,3}){3}"
        r"|192\.168(\.\d{1,3}){2}"
        r"|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2})(:\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["infra"])
async def health():
    return {"status": "ok", "environment": settings.environment}


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(clientes.router)
app.include_router(processos.router)
app.include_router(movimentacoes.router)
app.include_router(prazos.router)
app.include_router(briefing.router)
app.include_router(notificacoes.router)
app.include_router(sync_api.router)
app.include_router(config_api.router)
app.include_router(reunioes.router)
app.include_router(documentos.router)
app.include_router(financeiro.router)
app.include_router(whatsapp_api.router)
app.include_router(pagamentos_api.router)
app.include_router(dono.router)
app.include_router(mural.router)
app.include_router(aprendizado.router)
app.include_router(analise_api.router)
app.include_router(chat_ws.router)
