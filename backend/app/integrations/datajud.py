"""Cliente para a API Pública do DataJud (CNJ).

A API Pública do CNJ expõe, por tribunal, um endpoint Elasticsearch consultável
por número CNJ. A autenticação usa uma *API key pública* divulgada pelo próprio
CNJ (a mesma para todos). Pode ser sobrescrita via DATAJUD_API_KEY no .env.

Docs: https://datajud-wiki.cnj.jus.br/api-publica/
"""
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger("claudio.datajud")

BASE_URL = "https://api-publica.datajud.cnj.jus.br"

# API key pública divulgada pelo CNJ (fallback quando DATAJUD_API_KEY não é definida).
# O CNJ rotaciona esta chave periodicamente; a vigente fica em
# https://datajud-wiki.cnj.jus.br/api-publica/acesso (atualizada em 2026-11-22).
DEFAULT_PUBLIC_KEY = (
    "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
)

# Mapa de códigos de TR (justiça federal, segmento J=4) -> alias TRF.
_TRF = {"01": "trf1", "02": "trf2", "03": "trf3", "04": "trf4", "05": "trf5", "06": "trf6"}

# UF por código de TR na justiça estadual (segmento J=8).
_TJ_UF = {
    "01": "ac", "02": "al", "03": "ap", "04": "am", "05": "ba", "06": "ce",
    "07": "df", "08": "es", "09": "go", "10": "ma", "11": "mt", "12": "ms",
    "13": "mg", "14": "pa", "15": "pb", "16": "pr", "17": "pe", "18": "pi",
    "19": "rj", "20": "rn", "21": "rs", "22": "ro", "23": "rr", "24": "sc",
    "25": "se", "26": "sp", "27": "to",
}

_SO_DIGITOS = re.compile(r"\D")


class DataJudError(Exception):
    pass


def normalizar_numero(numero: str) -> str:
    """Remove máscara, retornando os 20 dígitos do número CNJ."""
    return _SO_DIGITOS.sub("", numero or "")


def segmentos_cnj(numero: str) -> dict | None:
    """Decompõe NNNNNNN-DD.AAAA.J.TR.OOOO. Retorna None se inválido."""
    d = normalizar_numero(numero)
    if len(d) != 20:
        return None
    return {
        "sequencial": d[0:7],
        "dv": d[7:9],
        "ano": d[9:13],
        "segmento": d[13:14],  # J
        "tribunal": d[14:16],  # TR
        "origem": d[16:20],    # OOOO
    }


def alias_tribunal(numero: str) -> str | None:
    """Mapeia o número CNJ para o alias do endpoint DataJud (ex: 'api_publica_trf1')."""
    seg = segmentos_cnj(numero)
    if not seg:
        return None
    j, tr = seg["segmento"], seg["tribunal"]
    if j == "4":  # Justiça Federal
        alias = _TRF.get(tr)
    elif j == "8":  # Justiça Estadual
        uf = _TJ_UF.get(tr)
        alias = f"tj{uf}" if uf else None
    elif j == "5":  # Justiça do Trabalho
        alias = f"trt{int(tr)}" if tr.isdigit() else None
    else:
        alias = None
    return f"api_publica_{alias}" if alias else None


def _api_key() -> str:
    return settings.datajud_api_key or DEFAULT_PUBLIC_KEY


async def buscar_processo(numero: str, api_key: str | None = None) -> dict | None:
    """Consulta o processo pelo número CNJ. Retorna o _source do primeiro hit, ou None.

    `api_key` (quando informada) tem prioridade sobre o .env/chave pública — permite
    que a chave venha das Configurações do sistema (tabela configuracoes).
    """
    alias = alias_tribunal(numero)
    if not alias:
        logger.warning("Tribunal não mapeado para o número %s", numero)
        return None

    url = f"{BASE_URL}/{alias}/_search"
    chave = api_key or _api_key()
    headers = {"Authorization": f"APIKey {chave}", "Content-Type": "application/json"}
    query = {"query": {"match": {"numeroProcesso": normalizar_numero(numero)}}, "size": 1}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, headers=headers, json=query)
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return hits[0]["_source"] if hits else None
    except httpx.HTTPError as exc:
        logger.warning("Falha DataJud (%s): %s", numero, exc)
        raise DataJudError(str(exc)) from exc


async def testar_conexao(api_key: str | None = None) -> tuple[bool, str]:
    """Testa a autenticação na API do DataJud. (ok, detalhe).

    Usa uma consulta leve (match por número inexistente, size 0) — o `match_all`
    sobrecarrega o índice e volta 429. Um 429 significa que a *chave foi aceita*,
    só que o servidor estava ocupado; por isso é tratado como sucesso.
    """
    url = f"{BASE_URL}/api_publica_trf1/_search"
    chave = api_key or _api_key()
    headers = {"Authorization": f"APIKey {chave}", "Content-Type": "application/json"}
    corpo = {"query": {"match": {"numeroProcesso": "00000000000000000000"}}, "size": 0}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=corpo)
        if resp.status_code == 200:
            return True, "Conexão OK — chave aceita pelo DataJud."
        if resp.status_code in (401, 403):
            return False, "Chave rejeitada (401/403). Verifique a API key."
        if resp.status_code == 429:
            return True, "Chave aceita — DataJud ocupado no momento (429). Tente de novo em instantes."
        return False, f"Resposta inesperada do DataJud: HTTP {resp.status_code}."
    except httpx.HTTPError as exc:
        return False, f"Falha de conexão: {exc or 'tempo esgotado'}"


def extrair_movimentacoes(source: dict) -> list[dict]:
    """Normaliza os movimentos do _source do DataJud para o formato interno."""
    movimentos = source.get("movimentos", []) or []
    resultado = []
    for mov in movimentos:
        data_hora = mov.get("dataHora", "")
        nome = mov.get("nome") or "Movimentação"
        complementos = mov.get("complementosTabelados") or []
        extra = "; ".join(c.get("nome", "") for c in complementos if c.get("nome"))
        descricao = f"{nome}" + (f" — {extra}" if extra else "")
        resultado.append(
            {
                "data": data_hora[:10] if data_hora else None,
                "descricao": descricao,
                "codigo": mov.get("codigo"),
                "tipo": nome,
                "dados_brutos": mov,
            }
        )
    # Mais recentes primeiro
    return sorted(resultado, key=lambda m: m["data"] or "", reverse=True)


def extrair_metadados(source: dict) -> dict:
    """Extrai metadados úteis do processo (classe, assuntos, órgão, grau)."""
    classe = (source.get("classe") or {}).get("nome")
    assuntos = [a.get("nome") for a in (source.get("assuntos") or []) if a.get("nome")]
    orgao = (source.get("orgaoJulgador") or {}).get("nome")
    return {
        "classe": classe,
        "assuntos": assuntos,
        "orgao_julgador": orgao,
        "grau": source.get("grau"),
        "data_ajuizamento": (source.get("dataAjuizamento") or "")[:10] or None,
        "tribunal": source.get("tribunal"),
    }
