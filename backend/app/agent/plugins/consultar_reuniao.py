from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.services import embeddings


@register_plugin
class ConsultarReuniaoPlugin(BasePlugin):
    name = "consultar_reuniao"
    description = "Responde perguntas sobre o que foi dito em reuniões (busca semântica nas transcrições)."
    parameters = {
        "pergunta": {"type": "string", "required": False},
        "cliente_id": {"type": "integer", "required": False},
    }
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        pergunta = params.get("pergunta") or context.mensagem
        resultados = await embeddings.buscar_similar(
            context.db, pergunta, top_k=5, fonte_tipo="reuniao"
        )

        cliente_id = params.get("cliente_id")
        if cliente_id:
            resultados = [
                r for r in resultados if (r.get("metadata") or {}).get("cliente_id") == int(cliente_id)
            ]

        if not resultados:
            return PluginResult(
                success=True,
                display="Não encontrei nada nas reuniões sobre isso.",
            )

        linhas = ["📎 **Encontrei nas reuniões:**", ""]
        for r in resultados[:3]:
            trecho = (r["conteudo"] or "")[:300]
            linhas.append(f"• (reunião #{r['fonte_id']}, relevância {r['similaridade']}): {trecho}")

        return PluginResult(
            success=True,
            data={"resultados": len(resultados)},
            display="\n".join(linhas),
        )
