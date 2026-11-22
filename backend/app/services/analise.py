"""Serviço de 'Análise do dia' — análise aprofundada por processo + plano de ação.

Para cada processo ativo do advogado, reúne as NOVIDADES (movimentações novas desde
a última análise), pede à IA um resumo + um plano de ação (roteiro de execução) e
rascunha a mensagem para o cliente — que entra na fila de PRÉ-APROVAÇÃO (nunca é
enviada sozinha; o advogado revisa e libera).

A fonte das novidades é agnóstica: hoje vem do DataJud (automático) e do JusBrasil
(varredura no navegador do advogado, após login manual). A análise roda igual,
qualquer que seja a origem do andamento.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm import LLMUnavailable, gerar
from app.models.cliente import Cliente
from app.models.movimentacao import Movimentacao
from app.models.prazo import Prazo
from app.models.processo import Processo
from app.services import configuracoes as cfg
from app.services import whatsapp as wsvc

logger = logging.getLogger("claudio.analise")

# 1ª análise (sem marco salvo): olha a última semana.
JANELA_PRIMEIRA_ANALISE_DIAS = 7

# Palavras-gatilho -> ação sugerida (fallback quando a IA está indisponível).
_ACOES = [
    ("senten", "Avaliar cabimento de recurso (prazo correndo) e comunicar o resultado ao cliente."),
    ("acórdã", "Analisar o acórdão e decidir sobre recurso às instâncias superiores."),
    ("acorda", "Analisar o acórdão e decidir sobre recurso às instâncias superiores."),
    ("intima", "Cumprir a intimação dentro do prazo (manifestar-se / protocolar)."),
    ("cita", "Preparar contestação / resposta dentro do prazo da citação."),
    ("perícia", "Agendar e preparar o cliente para a perícia; conferir os documentos."),
    ("pericia", "Agendar e preparar o cliente para a perícia; conferir os documentos."),
    ("audiênc", "Preparar cliente e testemunhas para a audiência; revisar a estratégia."),
    ("audienc", "Preparar cliente e testemunhas para a audiência; revisar a estratégia."),
    ("despacho", "Ler o despacho e cumprir eventual determinação do juízo."),
    ("juntada", "Conferir o documento juntado e avaliar se exige manifestação."),
]


def _marco_chave(advogado_id: int) -> str:
    return f"analise_visto_ate_{advogado_id}"


async def _desde(db: AsyncSession, advogado_id: int, explicito: datetime | None) -> datetime:
    if explicito:
        return explicito
    marco = await cfg.obter(db, _marco_chave(advogado_id))
    if marco:
        try:
            return datetime.fromisoformat(marco)
        except ValueError:
            pass
    return datetime.now(timezone.utc) - timedelta(days=JANELA_PRIMEIRA_ANALISE_DIAS)


def _plano_fallback(novidades: list[dict], prazos: list[dict]) -> list[str]:
    passos: list[str] = []
    textos = " ".join(n["descricao"].lower() for n in novidades)
    for chave, acao in _ACOES:
        if chave in textos and acao not in passos:
            passos.append(acao)
    for p in prazos:
        passos.append(f"Cumprir prazo: {p['descricao']} (vence {p['data_limite']}).")
    if not passos:
        passos.append("Revisar o andamento e registrar a próxima providência no processo.")
    return passos


async def _analisar_ia(
    numero: str, cliente_nome: str, novidades: list[dict], prazos: list[dict]
) -> dict:
    """Pede à IA {resumo, plano_acao[], mensagem_cliente}. Cai em regras se indisponível."""
    lista = "\n".join(f"- {n['data']}: {n['descricao']}" for n in novidades)
    prazos_txt = "\n".join(f"- {p['descricao']} (vence {p['data_limite']})" for p in prazos) or "nenhum"
    primeiro = (cliente_nome or "cliente").split()[0] if cliente_nome else "cliente"
    try:
        system = (
            "Você é um assistente jurídico de um escritório de advocacia previdenciária. "
            "Analise as novidades do processo e responda APENAS com um JSON no formato "
            '{"resumo": "...", "plano_acao": ["passo 1", "passo 2"], "mensagem_cliente": "..."}. '
            "O 'resumo' explica, em linguagem técnica e objetiva, o que mudou. "
            "O 'plano_acao' são passos práticos e concretos que o advogado deve executar agora. "
            "A 'mensagem_cliente' é curta, em português simples, sem juridiquês, cordial, no "
            "máximo 3 frases, sem prometer resultados; assine como 'Equipe do escritório'."
        )
        prompt = (
            f"Processo: {numero}\nCliente: {primeiro}\n"
            f"Novidades (mais recentes primeiro):\n{lista}\n\n"
            f"Prazos pendentes:\n{prazos_txt}\n\nJSON:"
        )
        bruto = await gerar(prompt, system=system, temperatura=0.3)
        inicio, fim = bruto.index("{"), bruto.rindex("}") + 1
        dados = json.loads(bruto[inicio:fim])
        resumo = (dados.get("resumo") or "").strip()
        plano = [p.strip() for p in (dados.get("plano_acao") or []) if p and p.strip()]
        msg = (dados.get("mensagem_cliente") or "").strip()
        if resumo and plano and msg:
            return {"resumo": resumo, "plano_acao": plano, "mensagem_cliente": msg, "fonte_ia": "llm"}
    except (LLMUnavailable, ValueError, json.JSONDecodeError, AttributeError):
        pass

    # Fallback por regras (sem IA)
    resumo = f"{len(novidades)} novidade(s): " + "; ".join(n["descricao"] for n in novidades[:3])
    plano = _plano_fallback(novidades, prazos)
    msg = await wsvc.mensagem_movimentacao(cliente_nome, numero, novidades[0]["descricao"])
    return {"resumo": resumo, "plano_acao": plano, "mensagem_cliente": msg, "fonte_ia": "regras"}


async def analise_do_dia(
    db: AsyncSession, advogado_id: int, desde: datetime | None = None, criar_rascunhos: bool = False
) -> dict:
    """Monta a análise do dia do advogado.

    criar_rascunhos=False → só analisa (somente leitura, pode chamar à vontade).
    criar_rascunhos=True  → grava a mensagem de cada processo na fila de pré-aprovação.
    """
    desde_dt = await _desde(db, advogado_id, desde)
    processos = (
        await db.execute(
            select(Processo).where(
                Processo.advogado_id == advogado_id, Processo.status == "ativo"
            )
        )
    ).scalars().all()

    itens: list[dict] = []
    for proc in processos:
        novas = (
            await db.execute(
                select(Movimentacao)
                .where(
                    Movimentacao.processo_id == proc.id,
                    Movimentacao.created_at >= desde_dt,
                )
                .order_by(Movimentacao.data.desc())
            )
        ).scalars().all()
        if not novas:
            continue

        novidades = [
            {"data": m.data.isoformat() if m.data else None, "descricao": m.descricao, "fonte": m.fonte}
            for m in novas
        ]
        prazos_rows = (
            await db.execute(
                select(Prazo)
                .where(Prazo.processo_id == proc.id, Prazo.status == "pendente")
                .order_by(Prazo.data_limite_util)
            )
        ).scalars().all()
        prazos = [
            {"descricao": p.descricao, "data_limite": p.data_limite_util.isoformat()}
            for p in prazos_rows
        ]

        cliente = await db.get(Cliente, proc.cliente_id) if proc.cliente_id else None
        analise = await _analisar_ia(proc.numero, cliente.nome if cliente else "", novidades, prazos)

        mensagem_pendente_id = None
        if criar_rascunhos and cliente:
            msg = await wsvc.criar_pendente(
                db, cliente, analise["mensagem_cliente"], gatilho="analise",
                usuario_id=advogado_id, processo_id=proc.id, auto_aprovar=False,
            )
            mensagem_pendente_id = msg.id if msg else None

        itens.append(
            {
                "processo_id": proc.id,
                "numero": proc.numero,
                "cliente": cliente.nome if cliente else None,
                "novidades": novidades,
                "prazos_pendentes": prazos,
                "resumo": analise["resumo"],
                "plano_acao": analise["plano_acao"],
                "mensagem_cliente": analise["mensagem_cliente"],
                "mensagem_pendente_id": mensagem_pendente_id,
                "fonte_ia": analise["fonte_ia"],
            }
        )

    return {
        "advogado_id": advogado_id,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "desde": desde_dt.isoformat(),
        "total_processos_com_novidade": len(itens),
        "itens": itens,
    }


async def marcar_visto(db: AsyncSession, advogado_id: int, quando: datetime | None = None) -> None:
    """Marca 'li a análise até agora' — as próximas só mostram o que vier depois disto."""
    quando = quando or datetime.now(timezone.utc)
    await cfg.definir(
        db, _marco_chave(advogado_id), quando.isoformat(),
        descricao="Última análise do dia marcada como vista",
    )
