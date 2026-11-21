"""Importa os plugins para disparar o auto-registro via @register_plugin."""
from app.agent.plugins import (  # noqa: F401
    ajuda,
    buscar_cliente,
    gerar_briefing,
    ler_processo,
    listar_processos,
    sugerir_tese,
    verificar_prazos,
)
