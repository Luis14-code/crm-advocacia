"""Cliente LLM (Ollama) com degradação graciosa quando indisponível."""
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger("claudio.llm")


class LLMUnavailable(Exception):
    pass


async def gerar(prompt: str, system: str | None = None, temperatura: float = 0.2) -> str:
    """Gera texto via Ollama. Levanta LLMUnavailable se o serviço não responder."""
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperatura},
    }
    if system:
        payload["system"] = system
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            resp = await client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("Ollama indisponível: %s", exc)
        raise LLMUnavailable(str(exc)) from exc


async def classificar_intencao(mensagem: str, plugins_desc: str) -> dict | None:
    """Pede ao LLM para escolher um plugin e extrair parâmetros. Retorna None se falhar."""
    system = (
        "Você é um classificador de intenções. Dada a mensagem do usuário e a lista "
        "de plugins disponíveis, responda APENAS com um JSON no formato "
        '{\"plugin\": \"nome\", \"params\": {}}. Se nenhum plugin servir, use '
        '{\"plugin\": null, \"params\": {}}.'
    )
    prompt = f"Plugins disponíveis:\n{plugins_desc}\n\nMensagem: {mensagem}\n\nJSON:"
    try:
        bruto = await gerar(prompt, system=system, temperatura=0.0)
    except LLMUnavailable:
        return None
    try:
        inicio = bruto.index("{")
        fim = bruto.rindex("}") + 1
        return json.loads(bruto[inicio:fim])
    except (ValueError, json.JSONDecodeError):
        return None
