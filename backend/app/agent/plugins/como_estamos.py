from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.services import dono, mural


def _fmt(v) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@register_plugin
class ComoEstamosPlugin(BasePlugin):
    name = "como_estamos"
    description = "Panorama geral do escritório (faturamento, processos, êxito, conquistas) para o sócio."
    parameters: dict[str, Any] = {}
    requires_confirmation = False
    allowed_roles = ["socio"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        d = await dono.dashboard(context.db)
        m = await mural.feed(context.db)

        fat = d["faturamento"]
        var = f" ({fat['variacao']:+d}% vs mês anterior)" if fat.get("variacao") is not None else ""
        meta = f" · {fat['percentual_meta']}% da meta" if fat.get("percentual_meta") is not None else ""

        linhas = [
            "📊 **Como estamos**",
            "",
            f"Faturamento do mês: {_fmt(fat['mes_atual'])}{var}{meta}",
            f"Saldo do mês: {_fmt(d['caixa']['saldo_mes'])} · Projeção 30d: {_fmt(d['caixa']['projecao_30'])}",
            f"Processos ativos: {d['processos']['ativos']}",
            f"Prazos urgentes: {d['criticos']['prazos_urgentes']} · Inadimplentes: {d['criticos']['inadimplentes']}",
        ]

        top = d.get("taxa_exito_por_tipo") or []
        if top:
            linhas.append("")
            linhas.append("**Êxito por tipo:**")
            linhas += [f"• {t['chave']}: {t['taxa_exito']}% ({t['total']} casos)" for t in top[:4]]

        g = m["gamificacao"]
        linhas += [
            "",
            f"🏆 Streak de prazos: {g['streak_prazos']} · Acordos no mês: {g['acordos_mes']}",
        ]

        return PluginResult(success=True, data={"dashboard": d}, display="\n".join(linhas))
