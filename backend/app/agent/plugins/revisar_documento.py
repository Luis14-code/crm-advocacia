from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.llm import LLMUnavailable, gerar
from app.agent.registry import register_plugin
from app.models.documento import Documento

# Checklist heurístico usado quando o LLM está indisponível.
_CHECKLIST = [
    ("endereçamento", "Confirme o endereçamento ao juízo competente."),
    ("qualifica", "Verifique a qualificação completa das partes (nome, CPF, endereço)."),
    ("fato", "Os fatos estão narrados de forma clara e cronológica?"),
    ("direito", "A fundamentação cita dispositivos legais e teses aplicáveis?"),
    ("pedido", "Os pedidos são certos, determinados e coerentes com os fatos?"),
    ("valor", "Há valor da causa e requerimento de provas?"),
]


@register_plugin
class RevisarDocumentoPlugin(BasePlugin):
    name = "revisar_documento"
    description = "Revisa uma peça existente e sugere melhorias com justificativa."
    parameters = {"documento_id": {"type": "integer", "required": True}}
    requires_confirmation = False
    allowed_roles = ["socio", "advogado"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        doc_id = params.get("documento_id")
        if not doc_id:
            return PluginResult(success=False, display="Qual documento devo revisar? Informe o número.")

        doc = await context.db.get(Documento, int(doc_id))
        if not doc or not doc.conteudo:
            return PluginResult(success=False, display="Documento não encontrado ou vazio.")

        # Tenta revisão com LLM
        try:
            prompt = (
                "Revise a peça jurídica abaixo e liste de 3 a 6 sugestões de melhoria, "
                "cada uma com uma breve justificativa. Seja objetivo.\n\n"
                f"{doc.conteudo[:5000]}"
            )
            texto = await gerar(prompt, temperatura=0.2)
            if texto:
                return PluginResult(
                    success=True,
                    data={"documento_id": doc.id},
                    display=f"🔎 **Revisão do doc #{doc.id}:**\n\n{texto}",
                )
        except LLMUnavailable:
            pass

        # Fallback: checklist
        conteudo = doc.conteudo.lower()
        sugestoes = [
            f"• {dica}" for chave, dica in _CHECKLIST if chave not in conteudo
        ] or ["• A estrutura básica parece presente. Revise a redação e a coerência dos pedidos."]
        return PluginResult(
            success=True,
            data={"documento_id": doc.id},
            display=f"🔎 **Revisão do doc #{doc.id}** (checklist):\n\n" + "\n".join(sugestoes),
        )
