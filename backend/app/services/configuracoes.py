"""Serviço de configurações do escritório (integrações).

Resolução da chave DataJud (ordem de prioridade):
  1. Valor salvo no banco (cifrado)  → configurado pelo sócio na tela de Integrações
  2. DATAJUD_API_KEY no .env
  3. Chave pública padrão do CNJ (embutida em integrations.datajud)
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import criptografar, descriptografar
from app.integrations.datajud import DEFAULT_PUBLIC_KEY
from app.models.configuracao import Configuracao

# Chaves conhecidas
DATAJUD_API_KEY = "datajud_api_key"
JUSBRASIL_DEFAULT_TOKEN = "jusbrasil_default_token"
WAAKG_BASE_URL = "waakg_base_url"
WAAKG_API_KEY = "waakg_api_key"
WAAKG_SESSION_ID = "waakg_session_id"
WHATSAPP_AUTO_ENVIO = "whatsapp_auto_envio"  # "true"/"false" — gatilhos saem sem aprovação
# Pagamentos / banco
PAGAMENTOS_PROVEDOR = "pagamentos_provedor"   # asaas | paghiper | manual
PAGAMENTOS_API_KEY = "pagamentos_api_key"
PAGAMENTOS_BASE_URL = "pagamentos_base_url"

# Metadados das chaves expostas na UI (quais são secretas)
CHAVES_SECRETAS = {DATAJUD_API_KEY, JUSBRASIL_DEFAULT_TOKEN, WAAKG_API_KEY, PAGAMENTOS_API_KEY}


async def obter(db: AsyncSession, chave: str) -> str | None:
    """Retorna o valor (decifrado se secreto) ou None."""
    cfg = (
        await db.execute(select(Configuracao).where(Configuracao.chave == chave))
    ).scalar_one_or_none()
    if not cfg or cfg.valor is None:
        return None
    if cfg.secreto:
        return descriptografar(cfg.valor)
    return cfg.valor


async def definir(
    db: AsyncSession, chave: str, valor: str | None, secreto: bool = False, descricao: str | None = None
) -> None:
    """Cria/atualiza uma configuração. valor=None/"" remove o valor (volta ao padrão)."""
    cfg = (
        await db.execute(select(Configuracao).where(Configuracao.chave == chave))
    ).scalar_one_or_none()

    valor_armazenado = None
    if valor:
        valor_armazenado = criptografar(valor) if secreto else valor

    if cfg:
        cfg.valor = valor_armazenado
        cfg.secreto = secreto
        if descricao:
            cfg.descricao = descricao
    else:
        db.add(
            Configuracao(
                chave=chave, valor=valor_armazenado, secreto=secreto, descricao=descricao
            )
        )


async def get_datajud_api_key(db: AsyncSession) -> tuple[str, str]:
    """Resolve a chave DataJud. Retorna (chave, fonte) com fonte em db|env|publico."""
    do_banco = await obter(db, DATAJUD_API_KEY)
    if do_banco:
        return do_banco, "db"
    if settings.datajud_api_key:
        return settings.datajud_api_key, "env"
    return DEFAULT_PUBLIC_KEY, "publico"


async def get_jusbrasil_default_token(db: AsyncSession) -> str | None:
    return await obter(db, JUSBRASIL_DEFAULT_TOKEN)


async def get_waakg_config(db: AsyncSession) -> dict:
    """Configuração do gateway WA-AKG (base_url, api_key, session_id)."""
    base = await obter(db, WAAKG_BASE_URL)
    return {
        "base_url": (base or "http://wa-akg:3000").rstrip("/"),
        "api_key": await obter(db, WAAKG_API_KEY),
        "session_id": await obter(db, WAAKG_SESSION_ID) or "claudio",
    }


async def get_whatsapp_auto_envio(db: AsyncSession) -> bool:
    """Se True, gatilhos (movimentação, boleto) são enviados sem pré-aprovação. Padrão: True."""
    valor = await obter(db, WHATSAPP_AUTO_ENVIO)
    if valor is None:
        return True
    return valor.lower() in ("1", "true", "sim", "on")


async def get_pagamentos_config(db: AsyncSession) -> dict:
    """Configuração do provedor de pagamentos/banco (gateway de boleto)."""
    return {
        "provedor": await obter(db, PAGAMENTOS_PROVEDOR) or "manual",
        "api_key": await obter(db, PAGAMENTOS_API_KEY),
        "base_url": await obter(db, PAGAMENTOS_BASE_URL),
    }
