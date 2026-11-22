"""Jurimetria: taxa de êxito por tese/juiz/vara/tipo e comparativo entre advogados."""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agente import AuditLog, ResultadoCaso
from app.models.documento import Documento
from app.models.prazo import Prazo
from app.models.processo import Processo
from app.models.usuario import Usuario

DIMENSOES = {
    "tese": ResultadoCaso.tese,
    "juiz": ResultadoCaso.juiz,
    "vara": ResultadoCaso.vara,
}

EXITO = ("procedente", "parcial", "acordo")


async def taxa_exito_por(db: AsyncSession, dimensao: str = "tese", minimo: int = 1) -> list[dict]:
    coluna = DIMENSOES.get(dimensao)
    if coluna is None:
        # por tipo de processo
        rows = (
            await db.execute(
                select(Processo.tipo, ResultadoCaso.resultado, ResultadoCaso.valor_obtido, ResultadoCaso.tempo_dias)
                .join(Processo, ResultadoCaso.processo_id == Processo.id)
            )
        ).all()
        chave_fn = lambda r: r[0]  # noqa: E731
    else:
        rows = (
            await db.execute(select(coluna, ResultadoCaso.resultado, ResultadoCaso.valor_obtido, ResultadoCaso.tempo_dias))
        ).all()
        chave_fn = lambda r: r[0]  # noqa: E731

    agrup: dict[str, dict] = {}
    for r in rows:
        chave = chave_fn(r) or "—"
        g = agrup.setdefault(chave, {"total": 0, "exito": 0, "valores": [], "tempos": []})
        g["total"] += 1
        if r[1] in EXITO:
            g["exito"] += 1
        if r[2]:
            g["valores"].append(float(r[2]))
        if r[3]:
            g["tempos"].append(int(r[3]))

    resultado = []
    for chave, g in agrup.items():
        if g["total"] < minimo:
            continue
        resultado.append(
            {
                "chave": chave,
                "total": g["total"],
                "taxa_exito": round(100 * g["exito"] / g["total"]),
                "valor_medio": round(sum(g["valores"]) / len(g["valores"])) if g["valores"] else None,
                "tempo_medio_dias": round(sum(g["tempos"]) / len(g["tempos"])) if g["tempos"] else None,
            }
        )
    return sorted(resultado, key=lambda x: x["total"], reverse=True)


async def comparar_advogados(db: AsyncSession) -> list[dict]:
    advogados = (
        await db.execute(
            select(Usuario).where(Usuario.ativo.is_(True), Usuario.perfil.in_(["socio", "advogado"]))
        )
    ).scalars().all()

    resultado = []
    for adv in advogados:
        ativos = (
            await db.execute(
                select(func.count()).select_from(Processo).where(
                    Processo.advogado_id == adv.id, Processo.status == "ativo"
                )
            )
        ).scalar_one()
        encerrados = (
            await db.execute(
                select(func.count()).select_from(Processo).where(
                    Processo.advogado_id == adv.id, Processo.status == "encerrado"
                )
            )
        ).scalar_one()
        # Taxa de êxito dos casos com resultado registrado
        casos = (
            await db.execute(
                select(ResultadoCaso.resultado)
                .join(Processo, ResultadoCaso.processo_id == Processo.id)
                .where(Processo.advogado_id == adv.id)
            )
        ).scalars().all()
        com_exito = sum(1 for r in casos if r in EXITO)
        taxa = round(100 * com_exito / len(casos)) if casos else None
        prazos_cumpridos = (
            await db.execute(
                select(func.count()).select_from(Prazo).join(Processo, Prazo.processo_id == Processo.id)
                .where(Processo.advogado_id == adv.id, Prazo.status == "cumprido")
            )
        ).scalar_one()
        prazos_perdidos = (
            await db.execute(
                select(func.count()).select_from(Prazo).join(Processo, Prazo.processo_id == Processo.id)
                .where(Processo.advogado_id == adv.id, Prazo.status == "perdido")
            )
        ).scalar_one()
        pecas = (
            await db.execute(
                select(func.count()).select_from(Documento).where(Documento.autor_id == adv.id)
            )
        ).scalar_one()

        resultado.append(
            {
                "advogado_id": adv.id,
                "nome": adv.nome,
                "ativos": ativos,
                "encerrados": encerrados,
                "taxa_exito": taxa,
                "prazos_cumpridos": prazos_cumpridos,
                "prazos_perdidos": prazos_perdidos,
                "pecas_produzidas": pecas,
            }
        )
    return resultado


async def relatorio_advogado(db: AsyncSession, advogado_id: int) -> dict:
    todos = await comparar_advogados(db)
    alvo = next((a for a in todos if a["advogado_id"] == advogado_id), None)
    return alvo or {"advogado_id": advogado_id, "erro": "sem dados"}


async def relatorio_detalhado(db: AsyncSession, advogado_id: int) -> dict:
    """Desempenho detalhado de um colaborador: semana/mês, atrasados, atividade."""
    adv = await db.get(Usuario, advogado_id)
    if not adv:
        return {"erro": "colaborador não encontrado"}

    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)
    sem_dt = datetime.combine(inicio_semana, datetime.min.time())
    mes_dt = datetime.combine(inicio_mes, datetime.min.time())

    async def _count(stmt) -> int:
        return (await db.execute(stmt)).scalar_one()

    base = await relatorio_advogado(db, advogado_id)

    # Prazos
    prazos_q = select(func.count()).select_from(Prazo).join(Processo, Prazo.processo_id == Processo.id).where(Processo.advogado_id == advogado_id)
    atrasados = await _count(prazos_q.where(Prazo.status == "pendente", Prazo.data_limite_util < hoje))
    pendentes = await _count(prazos_q.where(Prazo.status == "pendente"))
    cumpridos_semana = await _count(prazos_q.where(Prazo.status == "cumprido", Prazo.data_conclusao >= inicio_semana))
    cumpridos_mes = await _count(prazos_q.where(Prazo.status == "cumprido", Prazo.data_conclusao >= inicio_mes))

    # Peças
    pecas_q = select(func.count()).select_from(Documento).where(Documento.autor_id == advogado_id)
    pecas_semana = await _count(pecas_q.where(Documento.created_at >= sem_dt))
    pecas_mes = await _count(pecas_q.where(Documento.created_at >= mes_dt))

    # Atividade (ações no sistema — proxy de tempo/dedicação, via audit_log)
    atv_q = select(func.count()).select_from(AuditLog).where(AuditLog.usuario_id == advogado_id)
    atividade_semana = await _count(atv_q.where(AuditLog.created_at >= sem_dt))
    atividade_mes = await _count(atv_q.where(AuditLog.created_at >= mes_dt))
    ultima_atividade = (
        await db.execute(select(func.max(AuditLog.created_at)).where(AuditLog.usuario_id == advogado_id))
    ).scalar_one_or_none()

    # Dias ativos no mês (dias distintos com atividade) — proxy de "período que fica mexendo"
    dias_ativos = (
        await db.execute(
            select(func.count(func.distinct(func.date(AuditLog.created_at))))
            .where(AuditLog.usuario_id == advogado_id, AuditLog.created_at >= mes_dt)
        )
    ).scalar_one()

    # Resultados (retorno que vem dando)
    res_rows = (
        await db.execute(
            select(ResultadoCaso.resultado, func.count())
            .join(Processo, ResultadoCaso.processo_id == Processo.id)
            .where(Processo.advogado_id == advogado_id)
            .group_by(ResultadoCaso.resultado)
        )
    ).all()
    resultados = {r: n for r, n in res_rows if r}

    return {
        **base,
        "nome": adv.nome,
        "perfil": adv.perfil,
        "prazos_atrasados": atrasados,
        "prazos_pendentes": pendentes,
        "prazos_cumpridos_semana": cumpridos_semana,
        "prazos_cumpridos_mes": cumpridos_mes,
        "pecas_semana": pecas_semana,
        "pecas_mes": pecas_mes,
        "atividade_semana": atividade_semana,
        "atividade_mes": atividade_mes,
        "dias_ativos_mes": dias_ativos,
        "ultima_atividade": ultima_atividade.isoformat() if ultima_atividade else None,
        "resultados": resultados,
    }
