from decimal import Decimal, InvalidOperation
from typing import Any

from app.agent.base import Action, AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.enums import Perfil
from app.models.processo import Processo
from app.services import financeiro as svc


def _fmt(v) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@register_plugin
class CalcularAcordoPlugin(BasePlugin):
    name = "calcular_acordo"
    description = "Simula um acordo: deduções (honorários, custas, impostos), líquido do cliente e comparativo."
    parameters = {
        "processo_id": {"type": "integer", "required": False},
        "valor_bruto": {"type": "number", "required": True},
        "parcelas": {"type": "integer", "required": False},
    }
    requires_confirmation = False
    allowed_roles = ["socio", "advogado"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        try:
            valor_bruto = Decimal(str(params.get("valor_bruto")))
        except (InvalidOperation, TypeError):
            return PluginResult(success=False, display="Qual o valor bruto do acordo?")

        processo = None
        if params.get("processo_id"):
            processo = await context.db.get(Processo, int(params["processo_id"]))
        if not processo:
            return PluginResult(
                success=False,
                display="Para qual processo é a simulação? Me diga o processo primeiro.",
            )
        if context.user.perfil == Perfil.advogado.value and processo.advogado_id != context.user.id:
            return PluginResult(success=False, display="Você não tem acesso a esse processo.")

        parcelas = int(params.get("parcelas") or 1)
        sim = await svc.simular_acordo(context.db, processo, valor_bruto, parcelas)

        d = sim["deducoes"]
        linhas = [
            f"💰 **Simulação de Acordo** — Processo {sim['processo']}",
            "",
            f"Valor bruto do acordo:          {_fmt(sim['valor_bruto'])}",
            f"(-) Honorários contratuais {d['honorarios_contratuais']['percentual']:.0f}%: {_fmt(d['honorarios_contratuais']['valor'])}",
            f"(-) Custas processuais:         {_fmt(d['custas_processuais'])}",
            f"(-) Despesas:                   {_fmt(d['despesas'])}",
            f"(-) Impostos (ISS {d['impostos']['iss_percentual']:.0f}%):        {_fmt(d['impostos']['valor'])}",
            "────────────────────────────────────",
            f"**Líquido para o cliente:**     {_fmt(sim['liquido_cliente'])}",
            f"**Honorários do escritório:**   {_fmt(sim['honorarios_escritorio'])}",
        ]
        comp = sim.get("comparativo_sentenca")
        if comp and comp.get("valor_estimado"):
            linhas += [
                "",
                f"📈 Comparativo (jurimetria interna, {comp['amostra']} casos): se levar à sentença, "
                f"estimativa {_fmt(comp['valor_estimado'])} ({comp['probabilidade_exito']}% de êxito).",
            ]
        if parcelas > 1:
            linhas += ["", f"Parcelamento em {parcelas}x:"]
            linhas += [f"  {p['parcela']}x {_fmt(p['valor'])} — vence {p['vencimento']}" for p in sim["parcelamento"][:12]]

        return PluginResult(
            success=True,
            data=sim,
            display="\n".join(linhas),
            actions=[Action(label="Recalcular com outro valor", plugin="calcular_acordo")],
        )
