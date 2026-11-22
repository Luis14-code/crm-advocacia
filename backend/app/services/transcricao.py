"""Transcrição de áudio (faster-whisper) + resumo e extração de fatos via LLM.

O faster-whisper é importado de forma preguiçosa: só o whisper-worker tem a lib
instalada, então o backend principal pode importar este módulo sem quebrar.
"""
import json
import logging

from app.agent.llm import LLMUnavailable, gerar
from app.config import settings

logger = logging.getLogger("claudio.transcricao")

_modelo = None  # cache do WhisperModel


def _get_modelo():
    global _modelo
    if _modelo is None:
        from faster_whisper import WhisperModel  # import lazy

        logger.info("Carregando modelo Whisper '%s' (%s)", settings.whisper_model, settings.whisper_device)
        _modelo = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _modelo


def transcrever_audio(caminho: str) -> dict:
    """Transcreve um arquivo de áudio. Retorna {texto, duracao_segundos}."""
    modelo = _get_modelo()
    segments, info = modelo.transcribe(caminho, language=settings.whisper_language, vad_filter=True)
    partes = [seg.text.strip() for seg in segments]
    texto = " ".join(p for p in partes if p)
    return {"texto": texto, "duracao_segundos": int(getattr(info, "duration", 0) or 0)}


async def resumir_e_extrair(transcricao: str) -> dict:
    """Gera resumo + fatos para petição + pendências. Usa LLM, com fallback heurístico."""
    system = (
        "Você é o Cláudio, assistente jurídico de um escritório de advocacia. A partir da "
        "transcrição de uma reunião entre advogado e cliente, monte um RELATÓRIO útil para o "
        "caso. Responda APENAS em JSON com as chaves: "
        "'resumo' (string — relatório claro em 1-2 parágrafos, destacando os PONTOS CRUCIAIS "
        "e juridicamente relevantes para a advocacia: o que o cliente busca, fatos centrais, "
        "riscos e próximos passos recomendados), "
        "'fatos_peticao' (lista de strings — fatos objetivos e datados que servem de base para "
        "a petição), "
        "'pendencias' (lista de strings — documentos a solicitar e providências a tomar). "
        "Seja objetivo e técnico, sem inventar fatos que não estejam na transcrição."
    )
    prompt = f"Transcrição da reunião:\n{transcricao[:6000]}\n\nRelatório em JSON:"
    try:
        bruto = await gerar(prompt, system=system, temperatura=0.1)
        inicio = bruto.index("{")
        fim = bruto.rindex("}") + 1
        dados = json.loads(bruto[inicio:fim])
        return {
            "resumo": dados.get("resumo", "")[:4000],
            "fatos_peticao": dados.get("fatos_peticao", [])[:20],
            "pendencias": dados.get("pendencias", [])[:20],
        }
    except (LLMUnavailable, ValueError, json.JSONDecodeError):
        # Fallback sem LLM: resumo = primeiras frases; sem extração automática.
        frases = [f.strip() for f in transcricao.split(".") if f.strip()]
        resumo = ". ".join(frases[:3])
        return {
            "resumo": (resumo + ".") if resumo else "Transcrição concluída.",
            "fatos_peticao": [],
            "pendencias": [],
        }
