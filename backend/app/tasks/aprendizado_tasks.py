"""Ciclo de aprendizado contínuo (Celery beat, diário/periódico).

- Gera embeddings dos feedbacks com correção (memória de longo prazo).
- Calcula taxa de aceitação por plugin; alerta o sócio se cair abaixo de 70%.
- Atualiza as preferências aprendidas de cada usuário (plugins mais usados).
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select

from app.database import async_session_factory
from app.models.agente import AuditLog, Feedback
from app.models.enums import Perfil
from app.models.notificacao import Notificacao
from app.models.usuario import Usuario
from app.services import embeddings
from app.tasks.celery_app import celery_app

logger = logging.getLogger("claudio.tasks.aprendizado")

LIMIAR_ACEITACAO = 70
MIN_AMOSTRA = 5


async def _indexar_feedbacks(db) -> int:
    corte = datetime.now(timezone.utc) - timedelta(hours=24)
    feedbacks = (
        await db.execute(
            select(Feedback).where(
                Feedback.created_at >= corte, Feedback.correcao.isnot(None)
            )
        )
    ).scalars().all()
    for fb in feedbacks:
        conteudo = f"{fb.sugestao or ''}\nCorreção: {fb.correcao}"
        await embeddings.indexar(
            db, "feedback", fb.id, conteudo, metadata={"contexto": fb.contexto}
        )
    return len(feedbacks)


async def _stats_e_alertas(db) -> list[dict]:
    rows = (
        await db.execute(
            select(
                Feedback.contexto,
                func.count().label("total"),
                func.sum(case((Feedback.util.is_(True), 1), else_=0)).label("uteis"),
            )
            .where(Feedback.util.isnot(None))
            .group_by(Feedback.contexto)
        )
    ).all()

    stats = []
    for contexto, total, uteis in rows:
        if not total or total < MIN_AMOSTRA:
            continue
        taxa = round(100 * (uteis or 0) / total)
        stats.append({"contexto": contexto, "total": total, "aceitacao": taxa})
        if taxa < LIMIAR_ACEITACAO:
            socios = (
                await db.execute(select(Usuario).where(Usuario.perfil == Perfil.socio.value))
            ).scalars().all()
            for s in socios:
                db.add(
                    Notificacao(
                        usuario_id=s.id,
                        tipo="sistema",
                        titulo="Aprendizado: queda de aceitação",
                        corpo=f"O item '{contexto}' está com {taxa}% de aceitação (< {LIMIAR_ACEITACAO}%).",
                    )
                )
    return stats


async def _atualizar_preferencias(db) -> int:
    usuarios = (await db.execute(select(Usuario).where(Usuario.ativo.is_(True)))).scalars().all()
    for u in usuarios:
        rows = (
            await db.execute(
                select(AuditLog.plugin, func.count().label("n"))
                .where(AuditLog.usuario_id == u.id, AuditLog.plugin.isnot(None))
                .group_by(AuditLog.plugin)
                .order_by(func.count().desc())
                .limit(5)
            )
        ).all()
        if rows:
            prefs = dict(u.preferencias or {})
            prefs["plugins_mais_usados"] = [p for p, _ in rows]
            u.preferencias = prefs
    return len(usuarios)


async def _ciclo() -> dict:
    async with async_session_factory() as db:
        indexados = await _indexar_feedbacks(db)
        stats = await _stats_e_alertas(db)
        prefs = await _atualizar_preferencias(db)
        await db.commit()
    resumo = {"feedbacks_indexados": indexados, "stats": stats, "usuarios_atualizados": prefs}
    logger.info("Ciclo de aprendizado: %s", resumo)
    return resumo


@celery_app.task(name="claudio.ciclo_aprendizado")
def ciclo_aprendizado() -> dict:
    return asyncio.run(_ciclo())
