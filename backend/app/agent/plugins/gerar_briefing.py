from typing import Any

from app.agent.base import Action, AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.enums import Perfil
from app.services import briefing as svc_briefing


def _bloco(titulo: str, itens: list[dict]) -> str:
    if not itens:
        return ""
    linhas = [f"{titulo}"]
    for it in itens:
        proc = it.get("processo", "—")
        desc = it.get("descricao") or it.get("tipo", "")
        extra = ""
        if it.get("data_limite"):
            extra = f" (vence {it['data_limite']})"
        elif it.get("dias_parado") is not None:
            extra = f" ({it['dias_parado']} dias parado)"
        linhas.append(f"• {proc}: {desc}{extra} → _{it.get('acao_sugerida','')}_")
    return "\n".join(linhas)


@register_plugin
class GerarBriefingPlugin(BasePlugin):
    name = "gerar_briefing"
    description = "Monta o briefing do dia por prioridade (urgente, atenção, acompanhamento)."
    parameters = {"advogado_id": {"type": "integer", "required": False}}
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        alvo = context.user.id
        # Só o sócio pode pedir o briefing de outro advogado
        if params.get("advogado_id") and context.user.perfil == Perfil.socio.value:
            alvo = int(params["advogado_id"])

        dados = await svc_briefing.gerar_briefing(context.db, alvo)

        blocos = []
        b = _bloco("🔴 **Urgente**", dados["urgente"])
        if b:
            blocos.append(b)
        b = _bloco("🟡 **Atenção**", dados["atencao"])
        if b:
            blocos.append(b)
        b = _bloco("🟢 **Acompanhamento**", dados["acompanhamento"])
        if b:
            blocos.append(b)

        corpo = "\n\n".join(blocos) if blocos else "Nada pendente para hoje. ☕"
        display = f"📋 **Briefing do dia** — {dados['resumo']}\n\n{corpo}"

        return PluginResult(
            success=True,
            data=dados,
            display=display,
            actions=[Action(label="Ver prazos", plugin="verificar_prazos")],
        )
