"""Tasks de sincronização de processos (DataJud/JusBrasil)."""
import asyncio
import logging

from sqlalchemy import select

from app.database import async_session_factory
from app.models.enums import StatusProcesso
from app.models.processo import Processo
from app.services import sync
from app.tasks.celery_app import celery_app

logger = logging.getLogger("claudio.tasks.sync")


async def _sincronizar_todos() -> dict:
    agregado = {"processos": 0, "novas": 0, "prazos": 0, "erros": 0}
    async with async_session_factory() as db:
        processos = (
            await db.execute(
                select(Processo).where(Processo.status == StatusProcesso.ativo.value)
            )
        ).scalars().all()

        for proc in processos:
            try:
                r = await sync.sincronizar_processo(db, proc)
                agregado["processos"] += 1
                agregado["novas"] += r["novas"]
                agregado["prazos"] += r["prazos"]
                if r.get("erro"):
                    agregado["erros"] += 1
            except Exception:  # noqa: BLE001
                logger.exception("Erro ao sincronizar %s", proc.numero)
                agregado["erros"] += 1
        await db.commit()
    logger.info("Sync concluído: %s", agregado)
    return agregado


@celery_app.task(name="claudio.sync_processos")
def sync_processos() -> dict:
    return asyncio.run(_sincronizar_todos())
