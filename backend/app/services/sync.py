"""Sincronização de processos: DataJud (primário) com fallback JusBrasil.

Para cada processo:
  1. Busca movimentações no DataJud.
  2. Faz upsert (dedup por data+descrição), detectando as novas.
  3. Gera notificações das novas movimentações.
  4. Detecta prazos sugeridos a partir de movimentações-gatilho (intimação, sentença…).
"""
import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import datajud
from app.integrations.datajud import DataJudError
from app.models.movimentacao import Movimentacao
from app.services import configuracoes as cfg
from app.models.notificacao import Notificacao
from app.models.prazo import Prazo
from app.models.processo import Processo
from app.services import prazos as sp

logger = logging.getLogger("claudio.sync")

# Movimentações que sugerem abertura de prazo -> (dias úteis, descrição do prazo)
GATILHOS_PRAZO = [
    ("intima", 15, "Prazo após intimação"),
    ("cita", 15, "Prazo para contestação (citação)"),
    ("senten", 15, "Prazo para recurso (sentença publicada)"),
    ("acórdã", 15, "Prazo para recurso (acórdão)"),
    ("acorda", 15, "Prazo para recurso (acórdão)"),
]


async def _chaves_existentes(db: AsyncSession, processo_id: int) -> set[tuple]:
    rows = (
        await db.execute(
            select(Movimentacao.data, Movimentacao.descricao).where(
                Movimentacao.processo_id == processo_id
            )
        )
    ).all()
    return {(r[0].isoformat() if r[0] else None, r[1]) for r in rows}


def _parse_data(valor) -> date | None:
    if not valor:
        return None
    try:
        return datetime.strptime(valor[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


async def _detectar_prazo(db: AsyncSession, processo: Processo, mov: dict) -> Prazo | None:
    texto = (mov.get("descricao") or "").lower()
    data_mov = _parse_data(mov.get("data"))
    if not data_mov:
        return None
    for chave, dias, descricao in GATILHOS_PRAZO:
        if chave in texto:
            limite = sp.adicionar_dias_uteis(data_mov, dias)
            # Evita duplicar prazo idêntico
            existe = (
                await db.execute(
                    select(Prazo).where(
                        Prazo.processo_id == processo.id,
                        Prazo.data_limite == limite,
                        Prazo.descricao.like(f"%{descricao}%"),
                    )
                )
            ).scalar_one_or_none()
            if existe:
                return None
            return Prazo(
                processo_id=processo.id,
                responsavel_id=processo.advogado_id,
                descricao=f"[auto] {descricao} ({mov.get('tipo')})",
                data_limite=limite,
                data_limite_util=sp.data_limite_util(limite),
            )
    return None


async def sincronizar_processo(
    db: AsyncSession, processo: Processo, criar_notificacoes: bool = True
) -> dict:
    """Sincroniza um processo. Retorna {novas, prazos, fonte, erro?}."""
    resultado = {"processo": processo.numero, "novas": 0, "prazos": 0, "fonte": None, "erro": None}

    try:
        api_key, _fonte = await cfg.get_datajud_api_key(db)
        source = await datajud.buscar_processo(processo.numero, api_key=api_key)
        resultado["fonte"] = "datajud"
    except DataJudError as exc:
        # Fallback: mantém o que já existe (dados do JusBrasil/manual previamente salvos)
        resultado["fonte"] = "parcial"
        resultado["erro"] = f"DataJud indisponível: {exc}"
        return resultado

    if not source:
        resultado["erro"] = "Processo não encontrado no DataJud"
        return resultado

    # Atualiza metadados do processo quando ausentes
    meta = datajud.extrair_metadados(source)
    if not processo.tribunal and meta.get("tribunal"):
        processo.tribunal = meta["tribunal"]
    if not processo.vara and meta.get("orgao_julgador"):
        processo.vara = meta["orgao_julgador"]
    processo.meta = {**(processo.meta or {}), "datajud": meta}

    existentes = await _chaves_existentes(db, processo.id)
    movimentacoes = datajud.extrair_movimentacoes(source)

    novas = 0
    prazos_criados = 0
    ultima_nova_desc: str | None = None
    for mov in movimentacoes:
        data_mov = _parse_data(mov.get("data"))
        chave = (data_mov.isoformat() if data_mov else None, mov["descricao"])
        if chave in existentes:
            continue
        db.add(
            Movimentacao(
                processo_id=processo.id,
                data=data_mov or date.today(),
                descricao=mov["descricao"],
                fonte="datajud",
                tipo=mov.get("tipo"),
                dados_brutos=mov.get("dados_brutos"),
            )
        )
        novas += 1
        if ultima_nova_desc is None:
            ultima_nova_desc = mov["descricao"]

        # Notificação da nova movimentação
        if criar_notificacoes and processo.advogado_id:
            db.add(
                Notificacao(
                    usuario_id=processo.advogado_id,
                    processo_id=processo.id,
                    tipo="movimentacao",
                    titulo=f"Nova movimentação — {processo.numero}",
                    corpo=mov["descricao"],
                )
            )

        # Detecção de prazo
        prazo = await _detectar_prazo(db, processo, mov)
        if prazo:
            db.add(prazo)
            prazos_criados += 1
            if criar_notificacoes and processo.advogado_id:
                db.add(
                    Notificacao(
                        usuario_id=processo.advogado_id,
                        processo_id=processo.id,
                        tipo="prazo",
                        titulo=f"Prazo detectado — {processo.numero}",
                        corpo=f"{prazo.descricao} — vence {prazo.data_limite_util.strftime('%d/%m/%Y')}",
                    )
                )

    # Gatilho WhatsApp: ao detectar movimentação nova, a IA gera uma mensagem amigável
    # e, se o auto-envio estiver ligado (padrão), envia direto (sem pré-aprovação).
    if novas and processo.cliente_id and ultima_nova_desc:
        from app.models.cliente import Cliente
        from app.services import whatsapp as wsvc

        cliente = await db.get(Cliente, processo.cliente_id)
        if cliente and cliente.telefone and not cliente.whatsapp_opt_out:
            texto = await wsvc.mensagem_movimentacao(cliente.nome, processo.numero, ultima_nova_desc)
            await wsvc.disparar(
                db, cliente, texto, gatilho="movimentacao",
                processo_id=processo.id, usuario_id=processo.advogado_id,
            )

    resultado["novas"] = novas
    resultado["prazos"] = prazos_criados
    return resultado


async def sincronizar_movimentacoes_externas(
    db: AsyncSession, processo: Processo, movimentacoes: list[dict], fonte: str = "jusbrasil"
) -> dict:
    """Upsert de movimentações vindas de fonte externa (userscript JusBrasil)."""
    existentes = await _chaves_existentes(db, processo.id)
    novas = 0
    for mov in movimentacoes:
        data_mov = _parse_data(mov.get("data"))
        chave = (data_mov.isoformat() if data_mov else None, mov["descricao"])
        if chave in existentes:
            continue
        db.add(
            Movimentacao(
                processo_id=processo.id,
                data=data_mov or date.today(),
                descricao=mov["descricao"],
                fonte=fonte,
                tipo=mov.get("tipo"),
                dados_brutos=mov.get("dados_brutos"),
            )
        )
        novas += 1
    return {"processo": processo.numero, "novas": novas, "fonte": fonte}
