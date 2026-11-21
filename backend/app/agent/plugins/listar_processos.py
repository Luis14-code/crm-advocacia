from typing import Any

from sqlalchemy import select

from app.agent.base import Action, AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.enums import Perfil
from app.models.processo import Processo


@register_plugin
class ListarProcessosPlugin(BasePlugin):
    name = "listar_processos"
    description = "Lista os processos do usuário logado, opcionalmente filtrando por status."
    parameters = {
        "status": {"type": "string", "required": False, "enum": ["ativo", "encerrado", "arquivado"]},
    }
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        stmt = select(Processo)
        if context.user.perfil in (Perfil.advogado.value, Perfil.estagiario.value):
            stmt = stmt.where(Processo.advogado_id == context.user.id)
        status = params.get("status")
        if status:
            stmt = stmt.where(Processo.status == status)
        else:
            stmt = stmt.where(Processo.status == "ativo")
        stmt = stmt.order_by(Processo.updated_at.desc()).limit(50)

        processos = (await context.db.execute(stmt)).scalars().all()

        if not processos:
            return PluginResult(
                success=True,
                display="Você não tem processos com esse filtro no momento.",
            )

        linhas = [
            f"• **{p.numero}** — {p.tipo}"
            + (f" / {p.subtipo}" if p.subtipo else "")
            + f" ({p.status})"
            for p in processos
        ]
        display = f"Você tem **{len(processos)}** processo(s):\n" + "\n".join(linhas)

        return PluginResult(
            success=True,
            data={"total": len(processos), "processos": [p.numero for p in processos]},
            display=display,
            actions=[Action(label="Ver prazos", plugin="ajuda")],
        )
