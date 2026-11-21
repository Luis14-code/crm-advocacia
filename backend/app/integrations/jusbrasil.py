"""Integração JusBrasil (fonte COMPLEMENTAR).

O JusBrasil não expõe uma API pública estável. A estratégia (Seção 9 da spec) é:
  1. Um userscript (Tampermonkey) roda no Chrome do advogado, autenticado com o
     token individual dele, extrai os dados das páginas e faz POST para o backend
     (endpoint /api/sync/jusbrasil).
  2. Este módulo normaliza o payload recebido e serve de fallback quando o DataJud
     não tem o dado.

Regra de ouro (Seção 9.4): sempre preferir DataJud; usar JusBrasil só como complemento.
"""
import logging

from app.core.security import descriptografar

logger = logging.getLogger("claudio.jusbrasil")


class JusBrasilIndisponivel(Exception):
    pass


def token_valido(token_criptografado: str | None) -> bool:
    if not token_criptografado:
        return False
    return bool(descriptografar(token_criptografado))


def normalizar_payload_userscript(payload: dict) -> dict:
    """Converte o payload enviado pelo userscript no formato interno de sync.

    Payload esperado:
      {
        "numero": "0001234-56.2024.8.10.0001",
        "movimentacoes": [{"data": "2024-10-15", "descricao": "...", "tipo": "..."}]
      }
    """
    numero = payload.get("numero")
    movimentacoes = []
    for mov in payload.get("movimentacoes", []) or []:
        if not mov.get("data") or not mov.get("descricao"):
            continue
        movimentacoes.append(
            {
                "data": mov["data"][:10],
                "descricao": mov["descricao"],
                "codigo": mov.get("codigo"),
                "tipo": mov.get("tipo") or "movimentacao",
                "dados_brutos": mov,
            }
        )
    return {"numero": numero, "movimentacoes": movimentacoes}
