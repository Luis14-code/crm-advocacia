"""Task diária: gera boletos das cobranças programadas e marca vencidos."""
import asyncio
import logging

from app.database import async_session_factory
from app.services import financeiro as fin
from app.tasks.celery_app import celery_app

logger = logging.getLogger("claudio.tasks.cobrancas")


async def _rodar() -> dict:
    async with async_session_factory() as db:
        vencidos = await fin.marcar_vencidos(db)
        cobr = await fin.processar_cobrancas(db)
        await db.commit()
    resumo = {"vencidos_marcados": vencidos, **cobr}
    logger.info("Cobranças: %s", resumo)
    return resumo


@celery_app.task(name="claudio.processar_cobrancas")
def processar_cobrancas() -> dict:
    return asyncio.run(_rodar())
