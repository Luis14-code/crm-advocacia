"""Conciliação bancária: baixa de pagamentos (webhook) e import de extrato (OFX/CSV)."""
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financeiro import Transacao

logger = logging.getLogger("claudio.conciliacao")

JANELA_MATCH_DIAS = 10
_STMTTRN = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL | re.IGNORECASE)


def _tag(bloco: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>([^<\r\n]+)", bloco, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_data(valor: str | None) -> date | None:
    if not valor:
        return None
    s = re.sub(r"\D", "", valor)[:8]
    try:
        return datetime.strptime(s, "%Y%m%d").date() if len(s) == 8 else None
    except ValueError:
        return None


async def registrar_pagamento(
    db: AsyncSession, referencia, valor, pagador: str | None, data_pagamento: str | None
) -> dict:
    """Dá baixa em um boleto a partir da notificação do gateway. Identifica a transação."""
    dt = _parse_data(data_pagamento) or date.today()
    transacao = None

    if referencia is not None:
        ref = str(referencia)
        if ref.isdigit():
            transacao = await db.get(Transacao, int(ref))
        if transacao is None:
            transacao = (
                await db.execute(select(Transacao).where(Transacao.boleto_id == ref))
            ).scalar_one_or_none()

    if transacao:
        transacao.status = "pago"
        transacao.data_pagamento = dt
        if pagador and not (transacao.descricao or "").strip():
            transacao.descricao = f"Pago por {pagador}"
        return {"conciliado": True, "transacao_id": transacao.id, "cliente_id": transacao.cliente_id}

    # Sem correspondência: registra o recebimento assim mesmo (entrada avulsa).
    nova = Transacao(
        tipo="entrada",
        categoria="recebimento",
        descricao=f"Recebimento{f' — {pagador}' if pagador else ''}",
        valor=Decimal(str(valor or 0)),
        data_pagamento=dt,
        status="pago",
    )
    db.add(nova)
    await db.flush()
    return {"conciliado": False, "transacao_id": nova.id, "cliente_id": None}


async def _ja_existe_extrato(db: AsyncSession, dt: date, valor: Decimal, descricao: str) -> bool:
    existe = (
        await db.execute(
            select(Transacao.id).where(
                Transacao.categoria == "extrato",
                Transacao.data_pagamento == dt,
                Transacao.valor == valor,
                Transacao.descricao == descricao,
            )
        )
    ).first()
    return existe is not None


async def _conciliar_entrada(db: AsyncSession, dt: date, valor: Decimal) -> Transacao | None:
    """Procura uma entrada pendente de mesmo valor, vencimento próximo, e dá baixa."""
    janela_ini = dt - timedelta(days=JANELA_MATCH_DIAS)
    janela_fim = dt + timedelta(days=JANELA_MATCH_DIAS)
    candidata = (
        await db.execute(
            select(Transacao)
            .where(
                Transacao.tipo == "entrada",
                Transacao.status.in_(["pendente", "vencido"]),
                Transacao.valor == valor,
                Transacao.data_vencimento >= janela_ini,
                Transacao.data_vencimento <= janela_fim,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if candidata:
        candidata.status = "pago"
        candidata.data_pagamento = dt
    return candidata


def _linhas_ofx(conteudo: str) -> list[dict]:
    linhas = []
    for bloco in _STMTTRN.findall(conteudo):
        valor = _tag(bloco, "TRNAMT")
        dt = _parse_data(_tag(bloco, "DTPOSTED"))
        nome = _tag(bloco, "NAME") or _tag(bloco, "MEMO") or "Lançamento"
        if valor is None or dt is None:
            continue
        try:
            v = Decimal(valor.replace(",", "."))
        except Exception:  # noqa: BLE001
            continue
        linhas.append({"data": dt, "valor": v, "descricao": nome[:200]})
    return linhas


def _linhas_csv(conteudo: str) -> list[dict]:
    linhas = []
    for linha in conteudo.splitlines():
        partes = [p.strip() for p in re.split(r"[;,]", linha)]
        if len(partes) < 3:
            continue
        dt = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(partes[0], fmt).date()
                break
            except ValueError:
                continue
        if dt is None:
            continue
        try:
            v = Decimal(partes[1].replace(".", "").replace(",", ".")) if "," in partes[1] else Decimal(partes[1])
        except Exception:  # noqa: BLE001
            continue
        linhas.append({"data": dt, "valor": v, "descricao": partes[2][:200]})
    return linhas


async def importar_extrato(db: AsyncSession, conteudo: str) -> dict:
    """Importa um extrato OFX ou CSV, concilia entradas e registra lançamentos novos."""
    linhas = _linhas_ofx(conteudo) if "<STMTTRN>" in conteudo.upper() else _linhas_csv(conteudo)
    conciliadas = 0
    novas = 0
    for ln in linhas:
        valor_abs = abs(ln["valor"])
        if ln["valor"] > 0:  # crédito (entrada)
            match = await _conciliar_entrada(db, ln["data"], valor_abs)
            if match:
                conciliadas += 1
                continue
        # Sem conciliação → registra o lançamento do extrato (evita duplicar)
        if await _ja_existe_extrato(db, ln["data"], valor_abs, ln["descricao"]):
            continue
        db.add(
            Transacao(
                tipo="entrada" if ln["valor"] > 0 else "saida",
                categoria="extrato",
                descricao=ln["descricao"],
                valor=valor_abs,
                data_pagamento=ln["data"],
                status="pago",
            )
        )
        novas += 1
    return {"lancamentos": len(linhas), "conciliadas": conciliadas, "novas": novas}
