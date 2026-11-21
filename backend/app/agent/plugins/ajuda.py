from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import plugins_para_perfil, register_plugin


@register_plugin
class AjudaPlugin(BasePlugin):
    name = "ajuda"
    description = "Explica o que o Cláudio pode fazer, listando os plugins disponíveis para o perfil."
    parameters: dict[str, Any] = {}
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        disponiveis = plugins_para_perfil(context.user.perfil)
        # Não lista o próprio "ajuda"
        itens = [p for p in disponiveis if p.name != self.name]
        linhas = [f"• **{p.name}** — {p.description}" for p in itens]
        display = (
            f"Olá, {context.user.nome.split()[0]}! Eu sou o Cláudio. Posso te ajudar com:\n"
            + "\n".join(linhas)
            + "\n\nÉ só me pedir em linguagem natural."
        )
        return PluginResult(
            success=True,
            data={"plugins": [p.name for p in itens]},
            display=display,
        )
