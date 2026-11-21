from datetime import date, timedelta
from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.services import financeiro as svc


def _fmt(v) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@register_plugin
class RelatorioFinanceiroPlugin(BasePlugin):
    name = "relatorio_financeiro"
    description = "Gera um relatório financeiro do período (entradas, saídas, saldo, inadimplência)."
    parameters = {
        "dias": {"type": "integer", "required": False, "description": "Janela em dias (padrão 30)"},
    }
    requires_confirmation = False
    allowed_roles = ["socio"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        dias = int(params.get("dias") or 30)
        fim = date.today()
        inicio = fim - timedelta(days=dias)
        rel = await svc.relatorio_periodo(context.db, inicio, fim)

        linhas = [
            f"📊 **Relatório financeiro** — últimos {dias} dias",
            "",
            f"Entradas:       {_fmt(rel['entradas'])}",
            f"Saídas:         {_fmt(rel['saidas'])}",
            f"**Saldo:**      {_fmt(rel['saldo'])}",
            f"A receber:      {_fmt(rel['a_receber'])}",
            f"Inadimplência:  {_fmt(rel['inadimplencia'])}",
        ]
        return PluginResult(success=True, data=rel, display="\n".join(linhas))
