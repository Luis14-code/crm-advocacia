"""Task de geração do briefing matinal."""
import asyncio
import logging

from sqlalchemy import select

from app.database import async_session_factory
from app.models.enums import Perfil
from app.models.notificacao import Notificacao
from app.models.usuario import Usuario
from app.services import briefing
from app.tasks.celery_app import celery_app

logger = logging.getLogger("claudio.tasks.briefing")

PERFIS_COM_BRIEFING = (Perfil.socio.value, Perfil.advogado.value)


async def _gerar_briefings() -> dict:
    total = 0
    async with async_session_factory() as db:
        advogados = (
            await db.execute(
                select(Usuario).where(
                    Usuario.ativo.is_(True), Usuario.perfil.in_(PERFIS_COM_BRIEFING)
                )
            )
        ).scalars().all()

        for adv in advogados:
            dados = await briefing.gerar_briefing(db, adv.id)
            db.add(
                Notificacao(
                    usuario_id=adv.id,
                    tipo="briefing",
                    titulo="Seu briefing do dia está pronto",
                    corpo=dados["resumo"],
                )
            )
            total += 1
        await db.commit()
    logger.info("Briefings gerados: %s", total)
    return {"briefings": total}


@celery_app.task(name="claudio.gerar_briefings")
def gerar_briefings() -> dict:
    return asyncio.run(_gerar_briefings())
