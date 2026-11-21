"""Serviço WhatsApp: templates, janela de envio, simulação de digitação e rate limit.

Estratégia anti-bloqueio (WA-AKG é gateway não-oficial):
- Baixo volume (human-in-the-loop: mensagens saem aprovadas uma a uma).
- Janela de horário (padrão 08h–20h).
- Rate limit: máximo por hora + intervalo mínimo entre envios.
- Simulação de digitação: presença 'composing' + atraso proporcional ao texto.
- Respeito a opt-out do cliente.
"""
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.waakg import WaakgClient
from app.models.cliente import Cliente
from app.models.whatsapp import MensagemWhatsapp
from app.services import configuracoes as cfg

logger = logging.getLogger("claudio.whatsapp")

BRT = timezone(timedelta(hours=-3))

TEMPLATES: dict[str, str] = {
    "movimentacao": "Olá, {nome}! Houve uma nova movimentação no seu processo {processo}. "
    "Qualquer dúvida, estamos à disposição. — {escritorio}",
    "boleto": "{nome}, o seu boleto de R$ {valor} vence em {data}. "
    "O link de pagamento foi enviado. Qualquer dúvida, conte com a gente!",
    "boleto_lembrete": "Oi, {nome}! Passando para lembrar que o boleto de R$ {valor} vence amanhã.",
    "boleto_vencido": "{nome}, identificamos que o boleto de {data} está em aberto. "
    "Podemos ajudar com a regularização?",
    "aniversario": "Parabéns, {nome}! 🎉 O escritório {escritorio} deseja um ótimo dia!",
    "satisfacao": "{nome}, como foi sua experiência conosco? Seu retorno nos ajuda muito!",
}


def render_template(nome: str, contexto: dict) -> str:
    modelo = TEMPLATES.get(nome, "{texto}")
    try:
        return modelo.format(**{"escritorio": "Escritório", **contexto})
    except KeyError:
        return modelo


async def cliente_waakg(db: AsyncSession) -> WaakgClient | None:
    conf = await cfg.get_waakg_config(db)
    if not conf.get("api_key"):
        return None
    return WaakgClient(conf["base_url"], conf["api_key"], conf["session_id"])


def dentro_da_janela(agora: datetime | None = None) -> bool:
    agora = agora or datetime.now(BRT)
    return settings.whatsapp_envio_inicio <= agora.hour < settings.whatsapp_envio_fim


def segundos_ate_janela(agora: datetime | None = None) -> int:
    """Segundos até a próxima janela de envio (se estiver fora dela)."""
    agora = agora or datetime.now(BRT)
    if dentro_da_janela(agora):
        return 0
    alvo = agora.replace(hour=settings.whatsapp_envio_inicio, minute=0, second=0, microsecond=0)
    if agora.hour >= settings.whatsapp_envio_fim:
        alvo += timedelta(days=1)
    return max(60, int((alvo - agora).total_seconds()))


def delay_digitacao(texto: str) -> float:
    """Atraso (s) que simula alguém digitando: ~60ms/char, com piso/teto e jitter."""
    base = min(max(len(texto) * 0.06, 2.0), 12.0)
    return round(base + random.uniform(0.5, 2.5), 1)


async def _enviadas_na_ultima_hora(db: AsyncSession) -> int:
    corte = datetime.now(timezone.utc) - timedelta(hours=1)
    return (
        await db.execute(
            select(func.count())
            .select_from(MensagemWhatsapp)
            .where(
                MensagemWhatsapp.direcao == "saida",
                MensagemWhatsapp.status == "enviada",
                MensagemWhatsapp.enviada_em >= corte,
            )
        )
    ).scalar_one()


async def _segundos_desde_ultimo_envio(db: AsyncSession) -> int | None:
    ultima = (
        await db.execute(
            select(func.max(MensagemWhatsapp.enviada_em)).where(
                MensagemWhatsapp.direcao == "saida", MensagemWhatsapp.status == "enviada"
            )
        )
    ).scalar_one_or_none()
    if not ultima:
        return None
    return int((datetime.now(timezone.utc) - ultima).total_seconds())


async def espera_por_rate_limit(db: AsyncSession) -> int:
    """Retorna segundos a aguardar antes do próximo envio (0 = pode enviar agora)."""
    fora = segundos_ate_janela()
    if fora:
        return fora
    if await _enviadas_na_ultima_hora(db) >= settings.whatsapp_max_por_hora:
        return 600  # tenta de novo em 10 min
    desde = await _segundos_desde_ultimo_envio(db)
    if desde is not None and desde < settings.whatsapp_intervalo_min_seg:
        return settings.whatsapp_intervalo_min_seg - desde
    return 0


async def criar_pendente(
    db: AsyncSession,
    cliente: Cliente,
    texto: str,
    gatilho: str = "manual",
    usuario_id: int | None = None,
    processo_id: int | None = None,
    auto_aprovar: bool = False,
) -> MensagemWhatsapp | None:
    """Cria uma mensagem de saída aguardando confirmação (human-in-the-loop).

    Retorna None se o cliente optou por não receber ou não tem telefone.
    """
    if cliente.whatsapp_opt_out or not cliente.telefone:
        return None
    msg = MensagemWhatsapp(
        cliente_id=cliente.id,
        processo_id=processo_id,
        usuario_id=usuario_id,
        direcao="saida",
        telefone=cliente.telefone,
        texto=texto,
        gatilho=gatilho,
        status="aprovada" if auto_aprovar else "aguardando_confirmacao",
    )
    db.add(msg)
    await db.flush()
    return msg
