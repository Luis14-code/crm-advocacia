"""Serviço financeiro: simulador de acordo, fluxo de caixa, relatório, boletos."""
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agente import ResultadoCaso
from app.models.financeiro import ConfigHonorarios, Transacao
from app.models.processo import Processo

CENTAVO = Decimal("0.01")


def _q(v) -> Decimal:
    return Decimal(str(v)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


async def _percentual_honorarios(db: AsyncSession, tipo: str) -> Decimal:
    cfg = (
        await db.execute(select(ConfigHonorarios).where(ConfigHonorarios.tipo_processo == tipo))
    ).scalar_one_or_none()
    if cfg and cfg.percentual_contratual is not None:
        return Decimal(str(cfg.percentual_contratual))
    return Decimal(str(settings.honorarios_padrao))


async def _somar(db: AsyncSession, processo_id: int, categoria: str) -> Decimal:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(Transacao.valor), 0)).where(
                Transacao.processo_id == processo_id,
                Transacao.categoria == categoria,
                Transacao.status.in_(["pendente", "vencido"]),
            )
        )
    ).scalar_one()
    return _q(total)


def _fluxo_parcelas(total: Decimal, parcelas: int, inicio: date | None = None) -> list[dict]:
    inicio = inicio or date.today()
    base = (total / parcelas).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    fluxo = []
    acumulado = Decimal("0")
    for i in range(1, parcelas + 1):
        valor = base if i < parcelas else _q(total - acumulado)
        acumulado += valor
        venc = inicio + timedelta(days=30 * i)
        fluxo.append({"parcela": i, "valor": float(valor), "vencimento": venc.isoformat()})
    return fluxo


async def _comparativo_sentenca(db: AsyncSession, processo: Processo) -> dict | None:
    """Estima resultado por jurimetria interna (média de valor obtido + % procedente)."""
    if not processo.tese_principal and not processo.tipo:
        return None
    stmt = select(ResultadoCaso).join(Processo, ResultadoCaso.processo_id == Processo.id).where(
        Processo.tipo == processo.tipo
    )
    casos = (await db.execute(stmt)).scalars().all()
    if not casos:
        return None
    com_exito = [c for c in casos if c.resultado in ("procedente", "parcial", "acordo")]
    valores = [float(c.valor_obtido) for c in casos if c.valor_obtido]
    prob = round(100 * len(com_exito) / len(casos))
    media = round(sum(valores) / len(valores)) if valores else None
    return {"probabilidade_exito": prob, "valor_estimado": media, "amostra": len(casos)}


async def simular_acordo(
    db: AsyncSession, processo: Processo, valor_bruto: Decimal, parcelas: int = 1
) -> dict:
    valor_bruto = _q(valor_bruto)
    pct = await _percentual_honorarios(db, processo.tipo)
    honorarios_contratuais = _q(valor_bruto * pct / 100)
    custas = await _somar(db, processo.id, "custas")
    despesas = await _somar(db, processo.id, "despesa")
    impostos = _q(honorarios_contratuais * Decimal(str(settings.iss_percentual)) / 100)

    liquido_cliente = _q(valor_bruto - honorarios_contratuais - custas - despesas)
    honorarios_escritorio = _q(honorarios_contratuais - impostos)

    return {
        "processo": processo.numero,
        "valor_bruto": float(valor_bruto),
        "deducoes": {
            "honorarios_contratuais": {"percentual": float(pct), "valor": float(honorarios_contratuais)},
            "custas_processuais": float(custas),
            "despesas": float(despesas),
            "impostos": {"iss_percentual": settings.iss_percentual, "valor": float(impostos)},
        },
        "liquido_cliente": float(liquido_cliente),
        "honorarios_escritorio": float(honorarios_escritorio),
        "parcelamento": _fluxo_parcelas(liquido_cliente, parcelas),
        "comparativo_sentenca": await _comparativo_sentenca(db, processo),
    }


async def fluxo_caixa(db: AsyncSession, inicio: date, fim: date) -> dict:
    rows = (
        await db.execute(
            select(Transacao.tipo, func.coalesce(func.sum(Transacao.valor), 0))
            .where(
                Transacao.status == "pago",
                Transacao.data_pagamento >= inicio,
                Transacao.data_pagamento <= fim,
            )
            .group_by(Transacao.tipo)
        )
    ).all()
    entradas = _q(next((v for t, v in rows if t == "entrada"), 0))
    saidas = _q(next((v for t, v in rows if t == "saida"), 0))

    # Inadimplência: boletos/entradas vencidos e não pagos
    inadimplencia = (
        await db.execute(
            select(func.coalesce(func.sum(Transacao.valor), 0)).where(
                Transacao.status == "vencido", Transacao.tipo == "entrada"
            )
        )
    ).scalar_one()

    # A receber (pendentes futuros)
    a_receber = (
        await db.execute(
            select(func.coalesce(func.sum(Transacao.valor), 0)).where(
                Transacao.status == "pendente", Transacao.tipo == "entrada"
            )
        )
    ).scalar_one()

    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "entradas": float(entradas),
        "saidas": float(saidas),
        "saldo": float(_q(entradas - saidas)),
        "inadimplencia": float(_q(inadimplencia)),
        "a_receber": float(_q(a_receber)),
    }


async def relatorio_periodo(db: AsyncSession, inicio: date, fim: date) -> dict:
    caixa = await fluxo_caixa(db, inicio, fim)
    por_categoria = (
        await db.execute(
            select(Transacao.categoria, Transacao.tipo, func.coalesce(func.sum(Transacao.valor), 0))
            .where(Transacao.status == "pago", Transacao.data_pagamento >= inicio, Transacao.data_pagamento <= fim)
            .group_by(Transacao.categoria, Transacao.tipo)
        )
    ).all()
    categorias = [
        {"categoria": c or "—", "tipo": t, "valor": float(_q(v))} for c, t, v in por_categoria
    ]
    return {**caixa, "por_categoria": categorias}


async def dashboard(db: AsyncSession) -> dict:
    """KPIs para o painel em tempo real (hoje, semana, mês)."""
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())  # segunda-feira
    inicio_mes = hoje.replace(day=1)

    async def _recebido(desde: date) -> Decimal:
        v = (
            await db.execute(
                select(func.coalesce(func.sum(Transacao.valor), 0)).where(
                    Transacao.status == "pago",
                    Transacao.tipo == "entrada",
                    Transacao.data_pagamento >= desde,
                )
            )
        ).scalar_one()
        return _q(v)

    caixa_mes = await fluxo_caixa(db, inicio_mes, hoje)
    return {
        "faturado_hoje": float(await _recebido(hoje)),
        "faturado_semana": float(await _recebido(inicio_semana)),
        "faturado_mes": float(await _recebido(inicio_mes)),
        "entradas_mes": caixa_mes["entradas"],
        "saidas_mes": caixa_mes["saidas"],
        "saldo_mes": caixa_mes["saldo"],
        "a_receber": caixa_mes["a_receber"],
        "inadimplencia": caixa_mes["inadimplencia"],
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }


async def gerar_boleto(
    db: AsyncSession, cliente_id: int, valor: Decimal, vencimento: date,
    processo_id: int | None = None, descricao: str | None = None,
) -> Transacao:
    """Emite um boleto via gateway configurado; se não houver, registra placeholder.

    A transação fica como 'entrada/pendente' e é conciliada quando o pagamento chega
    (webhook do gateway ou import de extrato).
    """
    from app.models.cliente import Cliente
    from app.services import configuracoes as cfg

    transacao = Transacao(
        processo_id=processo_id,
        cliente_id=cliente_id,
        tipo="entrada",
        categoria="boleto",
        descricao=descricao or "Honorários",
        valor=_q(valor),
        data_vencimento=vencimento,
        status="pendente",
    )
    db.add(transacao)
    await db.flush()  # garante transacao.id para usar como referência externa

    conf = await cfg.get_pagamentos_config(db)
    if conf.get("api_key") and conf.get("provedor") not in (None, "manual"):
        from app.integrations.pagamentos import PagamentosClient, PagamentosError

        cliente = await db.get(Cliente, cliente_id)
        client = PagamentosClient(conf["provedor"], conf["api_key"], conf.get("base_url"))
        try:
            res = await client.criar_cobranca(
                nome=cliente.nome if cliente else "Cliente",
                cpf=cliente.cpf if cliente else None,
                valor=float(_q(valor)),
                vencimento=vencimento.isoformat(),
                descricao=transacao.descricao,
                external_ref=str(transacao.id),
            )
            transacao.boleto_id = res.get("id")
            transacao.boleto_url = res.get("url")
        except PagamentosError:
            transacao.boleto_id = f"PENDENTE-{transacao.id}"
            transacao.boleto_url = None
    else:
        # Sem gateway: placeholder (referência = id da transação)
        transacao.boleto_id = f"PLACEHOLDER-{transacao.id}"
        transacao.boleto_url = "https://boleto.exemplo/placeholder"

    await db.flush()
    await db.refresh(transacao)
    return transacao
