"""Geração de peças processuais (markdown) e exportação para PDF."""
import io
import logging
from datetime import date

from app.agent.llm import LLMUnavailable, gerar
from app.models.cliente import Cliente
from app.models.processo import Processo
from app.services import teses as svc_teses

logger = logging.getLogger("claudio.pecas")

TIPOS = {
    "peticao_inicial": "PETIÇÃO INICIAL",
    "contestacao": "CONTESTAÇÃO",
    "recurso": "RECURSO",
    "manifestacao": "MANIFESTAÇÃO",
}


def _cabecalho(tipo: str, processo: Processo, cliente: Cliente | None) -> str:
    titulo = TIPOS.get(tipo, "PEÇA PROCESSUAL")
    vara = processo.vara or "JUÍZO COMPETENTE"
    linhas = [
        f"EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DA {vara.upper()}",
        "",
        f"Processo nº {processo.numero}",
        "",
    ]
    if cliente:
        qualificacao = f"**{cliente.nome}**"
        if cliente.cpf:
            qualificacao += f", inscrito(a) no CPF sob o nº {cliente.cpf}"
        linhas.append(
            f"{qualificacao}, por seu advogado que esta subscreve, vem, "
            f"respeitosamente, à presença de Vossa Excelência apresentar a presente"
        )
    linhas += ["", f"**{titulo}**", ""]
    return "\n".join(linhas)


def _secao_fatos(fatos: list[str]) -> str:
    if not fatos:
        return "## DOS FATOS\n\n_(descrever os fatos)_\n"
    itens = "\n".join(f"{i}. {f}" for i, f in enumerate(fatos, 1))
    return f"## DOS FATOS\n\n{itens}\n"


async def _secao_fundamentos(processo: Processo, fatos: list[str]) -> str:
    teses = svc_teses.sugerir(processo.tipo, processo.subtipo)
    base = "## DO DIREITO\n\n"
    # Tenta enriquecer com o LLM; se indisponível, usa as teses do catálogo.
    try:
        prompt = (
            f"Redija, de forma objetiva e técnica, a fundamentação jurídica (2 a 4 parágrafos) "
            f"de uma peça do tipo '{processo.tipo}/{processo.subtipo}'. "
            f"Fatos: {'; '.join(fatos) if fatos else 'não informados'}. "
            f"Teses aplicáveis: {'; '.join(teses[:3])}."
        )
        texto = await gerar(prompt, temperatura=0.3)
        if texto:
            return base + texto + "\n"
    except LLMUnavailable:
        pass
    pontos = "\n".join(f"- {t}" for t in teses[:4])
    return base + "Aplicam-se ao caso as seguintes teses:\n\n" + pontos + "\n"


def _secao_pedidos(tipo: str) -> str:
    comuns = [
        "a procedência do pedido, nos termos acima;",
        "a condenação da parte contrária ao pagamento de custas e honorários sucumbenciais;",
        "a produção de todas as provas em direito admitidas.",
    ]
    itens = "\n".join(f"{chr(97+i)}) {p}" for i, p in enumerate(comuns))
    return f"## DOS PEDIDOS\n\nRequer-se:\n\n{itens}\n"


async def gerar_peca(
    tipo: str,
    processo: Processo,
    cliente: Cliente | None,
    fatos: list[str] | None = None,
) -> str:
    """Monta a minuta da peça em markdown."""
    fatos = fatos or []
    partes = [
        _cabecalho(tipo, processo, cliente),
        _secao_fatos(fatos),
        await _secao_fundamentos(processo, fatos),
        _secao_pedidos(tipo),
        "\nNestes termos,\npede deferimento.\n",
        f"\n_{date.today().strftime('%d de %B de %Y')}_\n",
        "\n______________________________\nAdvogado(a)\n",
    ]
    return "\n".join(partes)


def markdown_para_pdf(conteudo_md: str, titulo: str = "Documento") -> bytes:
    """Converte markdown em PDF (markdown -> HTML -> PDF via xhtml2pdf)."""
    import markdown as md
    from xhtml2pdf import pisa

    html_corpo = md.markdown(conteudo_md, extensions=["extra", "sane_lists"])
    html = f"""
    <html><head><meta charset="utf-8"><style>
      @page {{ size: A4; margin: 2.5cm; }}
      body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; text-align: justify; }}
      h1, h2 {{ font-size: 12pt; }}
      h2 {{ margin-top: 18px; }}
    </style></head><body>{html_corpo}</body></html>
    """
    buffer = io.BytesIO()
    pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
    return buffer.getvalue()
