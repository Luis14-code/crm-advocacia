"""Task de envio de WhatsApp com simulação de digitação e rate limit."""
import asyncio
import logging
from datetime import datetime, timezone

from app.database import async_session_factory
from app.integrations.waakg import WaakgError, telefone_para_jid
from app.models.whatsapp import MensagemWhatsapp
from app.services import whatsapp as svc
from app.tasks.celery_app import celery_app

logger = logging.getLogger("claudio.tasks.whatsapp")


async def _enviar(mensagem_id: int) -> dict:
    async with async_session_factory() as db:
        msg = await db.get(MensagemWhatsapp, mensagem_id)
        if not msg or msg.direcao != "saida":
            return {"erro": "mensagem inválida"}
        if msg.status not in ("aprovada",):
            return {"ignorado": f"status {msg.status}"}

        client = await svc.cliente_waakg(db)
        if client is None:
            msg.status = "erro"
            msg.erro = "Gateway WA-AKG não configurado (defina a API key em Configurações)."
            await db.commit()
            return {"erro": msg.erro}

        # Janela / rate limit → reagenda se necessário
        espera = await svc.espera_por_rate_limit(db)
        if espera > 0:
            from app.tasks.whatsapp_tasks import enviar_whatsapp_task

            enviar_whatsapp_task.apply_async((mensagem_id,), countdown=min(espera, 3600))
            return {"reagendado_em_segundos": espera}

        jid = telefone_para_jid(msg.telefone or "")
        try:
            # Simulação de digitação
            await client.presenca(jid, "composing")
            await asyncio.sleep(svc.delay_digitacao(msg.texto))
            resposta = await client.enviar_texto(jid, msg.texto)
            await client.presenca(jid, "paused")

            msg.status = "enviada"
            msg.enviada_em = datetime.now(timezone.utc)
            data = resposta.get("data") or {}
            key = data.get("key") or {}
            msg.message_id = key.get("id")
            await db.commit()
            return {"status": "enviada", "message_id": msg.message_id}
        except WaakgError as exc:
            msg.status = "erro"
            msg.erro = str(exc)
            await db.commit()
            logger.warning("Falha no envio WhatsApp #%s: %s", mensagem_id, exc)
            return {"erro": str(exc)}


@celery_app.task(name="claudio.enviar_whatsapp")
def enviar_whatsapp_task(mensagem_id: int) -> dict:
    return asyncio.run(_enviar(mensagem_id))
