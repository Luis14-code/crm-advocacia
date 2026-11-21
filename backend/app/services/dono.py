"""Dashboard do dono (visão executiva, Seção 11). Exige senha sensível na API."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financeiro import Transacao
from app.models.prazo import Prazo
from app.models.processo import Processo
from app.services import configuracoes as cfg
from app.services import financeiro as fin
from app.services import jurimetria


def _q(v) -> float:
    return float(Decimal(str(v or 0)))


async def _faturamento_periodo(db: AsyncSession, inicio: date, fim: date) -> float:
    v = (
        await db.execute(
            select(func.coalesce(func.sum(Transacao.valor), 0)).where(
                Transacao.status == "pago",
                Transacao.tipo == "entrada",
                Transacao.data_pagamento >= inicio,
                Transacao.data_pagamento <= fim,
            )
        )
    ).scalar_one()
    return _q(v)


async def _projecao(db: AsyncSession, dias: int) -> float:
    hoje = date.today()
    v = (
        await db.execute(
            select(func.coalesce(func.sum(Transacao.valor), 0)).where(
                Transacao.status == "pendente",
                Transacao.tipo == "entrada",
                Transacao.data_vencimento <= hoje + timedelta(days=dias),
            )
        )
    ).scalar_one()
    return _q(v)


async def dashboard(db: AsyncSession) -> dict:
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    fim_mes_ant = inicio_mes - timedelta(days=1)
    inicio_mes_ant = fim_mes_ant.replace(day=1)

    fat_atual = await _faturamento_periodo(db, inicio_mes, hoje)
    fat_anterior = await _faturamento_periodo(db, inicio_mes_ant, fim_mes_ant)
    meta = await cfg.get_meta_faturamento(db)

    caixa = await fin.fluxo_caixa(db, inicio_mes, hoje)

    # Processos por status
    por_status = (
        await db.execute(select(Processo.status, func.count()).group_by(Processo.status))
    ).all()
    ativos = (
        await db.execute(select(func.count()).select_from(Processo).where(Processo.status == "ativo"))
    ).scalar_one()

    # Críticos
    prazos_urgentes = (
        await db.execute(
            select(func.count()).select_from(Prazo).where(
                Prazo.status == "pendente", Prazo.data_limite_util <= hoje + timedelta(days=3)
            )
        )
    ).scalar_one()
    inadimplentes = (
        await db.execute(
            select(func.count()).select_from(Transacao).where(
                Transacao.status == "vencido", Transacao.tipo == "entrada"
            )
        )
    ).scalar_one()

    return {
        "faturamento": {
            "mes_atual": fat_atual,
            "mes_anterior": fat_anterior,
            "meta": meta,
            "percentual_meta": round(100 * fat_atual / meta) if meta else None,
            "variacao": round(100 * (fat_atual - fat_anterior) / fat_anterior) if fat_anterior else None,
        },
        "caixa": {
            "saldo_mes": caixa["saldo"],
            "entradas": caixa["entradas"],
            "saidas": caixa["saidas"],
            "projecao_30": await _projecao(db, 30),
            "projecao_60": await _projecao(db, 60),
            "projecao_90": await _projecao(db, 90),
        },
        "processos": {
            "ativos": ativos,
            "por_status": [{"status": s, "total": n} for s, n in por_status],
        },
        "taxa_exito_por_tipo": await jurimetria.taxa_exito_por(db, "tipo"),
        "produtividade": await jurimetria.comparar_advogados(db),
        "criticos": {
            "prazos_urgentes": prazos_urgentes,
            "inadimplentes": inadimplentes,
        },
    }
