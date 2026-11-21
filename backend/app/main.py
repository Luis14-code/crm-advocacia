"""Aplicação FastAPI do Projeto Cláudio."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat_ws, clientes, processos, usuarios
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
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Sensitive-Token"],
)


@app.get("/api/health", tags=["infra"])
async def health():
    return {"status": "ok", "environment": settings.environment}


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(clientes.router)
app.include_router(processos.router)
app.include_router(chat_ws.router)
