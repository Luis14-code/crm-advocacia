"""Mural de conquistas (feed do 'escritório vivo') + gamificação leve.

Sem dados financeiros — visível a todos. Alimenta a sensação de escritório vivo.
"""
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agente import ResultadoCaso
from app.models.prazo import Prazo

EXITO = ("procedente", "parcial", "acordo")


async def feed(db: AsyncSession) -> dict:
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    # Conquistas de hoje (via created_at dos resultados)
    acordos_hoje = (
        await db.execute(
            select(func.count()).select_from(ResultadoCaso).where(
                ResultadoCaso.resultado == "acordo",
                func.date(ResultadoCaso.created_at) == hoje,
            )
        )
    ).scalar_one()
    sentencas_hoje = (
        await db.execute(
            select(func.count()).select_from(ResultadoCaso).where(
                ResultadoCaso.resultado.in_(["procedente", "parcial"]),
                func.date(ResultadoCaso.created_at) == hoje,
            )
        )
    ).scalar_one()
    prazos_cumpridos_hoje = (
        await db.execute(
            select(func.count()).select_from(Prazo).where(
                Prazo.status == "cumprido", Prazo.data_conclusao == hoje
            )
        )
    ).scalar_one()

    eventos = []
    if acordos_hoje:
        eventos.append({"icone": "🤝", "texto": f"{acordos_hoje} acordo(s) fechado(s) hoje"})
    if sentencas_hoje:
        eventos.append({"icone": "⚖️", "texto": f"{sentencas_hoje} sentença(s) favorável(is) hoje"})
    if prazos_cumpridos_hoje:
        eventos.append({"icone": "✅", "texto": f"{prazos_cumpridos_hoje} prazo(s) cumprido(s) hoje"})
    if not eventos:
        eventos.append({"icone": "☕", "texto": "Dia tranquilo até agora. Bora produzir!"})

    # Gamificação
    acordos_mes = (
        await db.execute(
            select(func.count()).select_from(ResultadoCaso).where(
                ResultadoCaso.resultado == "acordo",
                ResultadoCaso.created_at >= inicio_mes,
            )
        )
    ).scalar_one()
    cumpridos_mes = (
        await db.execute(
            select(func.count()).select_from(Prazo).where(
                Prazo.status == "cumprido", Prazo.data_conclusao >= inicio_mes
            )
        )
    ).scalar_one()
    perdidos_mes = (
        await db.execute(
            select(func.count()).select_from(Prazo).where(
                Prazo.status == "perdido", Prazo.data_conclusao >= inicio_mes
            )
        )
    ).scalar_one()

    # Streak: prazos cumpridos após o último perdido
    ultimo_perdido = (
        await db.execute(
            select(func.max(Prazo.data_conclusao)).where(Prazo.status == "perdido")
        )
    ).scalar_one_or_none()
    cond = [Prazo.status == "cumprido"]
    if ultimo_perdido:
        cond.append(Prazo.data_conclusao > ultimo_perdido)
    streak = (
        await db.execute(select(func.count()).select_from(Prazo).where(and_(*cond)))
    ).scalar_one()

    return {
        "data": hoje.isoformat(),
        "eventos": eventos,
        "gamificacao": {
            "streak_prazos": streak,
            "acordos_mes": acordos_mes,
            "prazos_cumpridos_mes": cumpridos_mes,
            "prazos_perdidos_mes": perdidos_mes,
        },
    }
