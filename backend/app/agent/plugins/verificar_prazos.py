from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.enums import Perfil
from app.models.prazo import Prazo
from app.models.processo import Processo


def _classificar(limite: date, hoje: date) -> tuple[str, str]:
    if limite < hoje:
        return "🔴", "atrasado"
    if limite == hoje:
        return "🔴", "vence hoje"
    if limite <= hoje + timedelta(days=3):
        return "🟡", "próximos 3 dias"
    return "🟢", "no prazo"


@register_plugin
class VerificarPrazosPlugin(BasePlugin):
    name = "verificar_prazos"
    description = "Lista os prazos pendentes do usuário, ordenados por urgência, com alertas."
    parameters: dict[str, Any] = {}
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        hoje = date.today()
        stmt = (
            select(Prazo, Processo.numero)
            .join(Processo, Prazo.processo_id == Processo.id)
            .where(Prazo.status == "pendente")
            .order_by(Prazo.data_limite_util)
        )
        if context.user.perfil in (Perfil.advogado.value, Perfil.estagiario.value):
            stmt = stmt.where(Processo.advogado_id == context.user.id)

        linhas_itens = (await context.db.execute(stmt)).all()
        if not linhas_itens:
            return PluginResult(success=True, display="🟢 Você não tem prazos pendentes. Tudo em dia!")

        linhas = []
        for prazo, numero in linhas_itens:
            icone, situacao = _classificar(prazo.data_limite_util, hoje)
            linhas.append(
                f"{icone} **{prazo.data_limite_util.strftime('%d/%m/%Y')}** "
                f"({situacao}) — {numero}: {prazo.descricao}"
            )

        return PluginResult(
            success=True,
            data={"total": len(linhas_itens)},
            display=f"Você tem **{len(linhas_itens)}** prazo(s) pendente(s):\n" + "\n".join(linhas),
        )
