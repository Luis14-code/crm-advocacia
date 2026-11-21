"""Importa os plugins para disparar o auto-registro via @register_plugin."""
from app.agent.plugins import (  # noqa: F401
    ajuda,
    buscar_cliente,
    calcular_acordo,
    como_estamos,
    consultar_reuniao,
    enviar_whatsapp,
    gerar_boleto,
    gerar_briefing,
    gerar_peca,
    ler_processo,
    listar_processos,
    relatorio_financeiro,
    revisar_documento,
    sugerir_tese,
    transcrever_reuniao,
    verificar_prazos,
)
