"""Montagem do briefing diário por prioridade (Seção 5.2).

Prioridade: prazos vencendo hoje > prazos da semana > movimentações novas
            > processos parados > acompanhamento geral.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movimentacao import Movimentacao
from app.models.prazo import Prazo
from app.models.processo import Processo

DIAS_PARADO_PADRAO = 30
JANELA_MOV_NOVAS_HORAS = 48


async def gerar_briefing(
    db: AsyncSession, advogado_id: int, dias_parado: int = DIAS_PARADO_PADRAO
) -> dict:
    hoje = date.today()
    fim_semana = hoje + timedelta(days=7)

    urgente: list[dict] = []
    atencao: list[dict] = []
    acompanhamento: list[dict] = []

    # --- Prazos pendentes do advogado ---
    prazos = (
        await db.execute(
            select(Prazo, Processo.numero)
            .join(Processo, Prazo.processo_id == Processo.id)
            .where(Processo.advogado_id == advogado_id, Prazo.status == "pendente")
            .order_by(Prazo.data_limite_util)
        )
    ).all()

    for prazo, numero in prazos:
        limite = prazo.data_limite_util
        if limite <= hoje:
            urgente.append(
                {
                    "processo": numero,
                    "tipo": "prazo_hoje" if limite == hoje else "prazo_atrasado",
                    "descricao": prazo.descricao,
                    "data_limite": limite.isoformat(),
                    "acao_sugerida": "Protocolar / cumprir prazo",
                }
            )
        elif limite <= fim_semana:
            atencao.append(
                {
                    "processo": numero,
                    "tipo": "prazo_semana",
                    "descricao": prazo.descricao,
                    "data_limite": limite.isoformat(),
                    "acao_sugerida": "Preparar peça do prazo",
                }
            )

    # --- Movimentações novas (últimas 48h) ---
    limite_mov = datetime.utcnow() - timedelta(hours=JANELA_MOV_NOVAS_HORAS)
    movs = (
        await db.execute(
            select(Movimentacao, Processo.numero)
            .join(Processo, Movimentacao.processo_id == Processo.id)
            .where(Processo.advogado_id == advogado_id, Movimentacao.created_at >= limite_mov)
            .order_by(Movimentacao.data.desc())
            .limit(20)
        )
    ).all()
    for mov, numero in movs:
        atencao.append(
            {
                "processo": numero,
                "tipo": "movimentacao_nova",
                "descricao": mov.descricao,
                "acao_sugerida": "Analisar e decidir próximo passo",
            }
        )

    # --- Processos parados ---
    corte_parado = hoje - timedelta(days=dias_parado)
    processos_ativos = (
        await db.execute(
            select(Processo).where(
                Processo.advogado_id == advogado_id, Processo.status == "ativo"
            )
        )
    ).scalars().all()

    for proc in processos_ativos:
        ultima = (
            await db.execute(
                select(func.max(Movimentacao.data)).where(Movimentacao.processo_id == proc.id)
            )
        ).scalar_one_or_none()
        if ultima is None or ultima < corte_parado:
            dias = (hoje - ultima).days if ultima else None
            acompanhamento.append(
                {
                    "processo": proc.numero,
                    "tipo": "parado",
                    "dias_parado": dias,
                    "acao_sugerida": "Peticionar solicitando andamento",
                }
            )

    resumo = (
        f"{len(urgente)} urgente(s), {len(atencao)} em atenção, "
        f"{len(acompanhamento)} em acompanhamento"
    )

    return {
        "advogado_id": advogado_id,
        "data": hoje.isoformat(),
        "urgente": urgente,
        "atencao": atencao,
        "acompanhamento": acompanhamento,
        "resumo": resumo,
    }
