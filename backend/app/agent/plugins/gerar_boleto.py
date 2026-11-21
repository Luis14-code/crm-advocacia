from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.cliente import Cliente
from app.services import financeiro as svc


@register_plugin
class GerarBoletoPlugin(BasePlugin):
    name = "gerar_boleto"
    description = "Gera um boleto (cobrança) para um cliente com valor e vencimento."
    parameters = {
        "cliente_id": {"type": "integer", "required": True},
        "valor": {"type": "number", "required": True},
        "vencimento": {"type": "string", "required": True, "description": "AAAA-MM-DD"},
        "processo_id": {"type": "integer", "required": False},
        "descricao": {"type": "string", "required": False},
    }
    requires_confirmation = True
    allowed_roles = ["socio", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        cliente_id = params.get("cliente_id")
        if not cliente_id:
            return PluginResult(success=False, display="Para qual cliente é o boleto?")
        cliente = await context.db.get(Cliente, int(cliente_id))
        if not cliente:
            return PluginResult(success=False, display="Cliente não encontrado.")

        try:
            valor = Decimal(str(params.get("valor")))
        except (InvalidOperation, TypeError):
            return PluginResult(success=False, display="Qual o valor do boleto?")

        try:
            venc = datetime.strptime(str(params.get("vencimento")), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            venc = date.today()

        transacao = await svc.gerar_boleto(
            context.db, cliente.id, valor, venc,
            processo_id=params.get("processo_id"), descricao=params.get("descricao"),
        )
        return PluginResult(
            success=True,
            data={"transacao_id": transacao.id, "boleto_url": transacao.boleto_url},
            display=(
                f"🧾 Boleto gerado para **{cliente.nome}**: R$ {float(valor):.2f}, "
                f"vence {venc.strftime('%d/%m/%Y')}.\n"
                "_(placeholder — integração com gateway real de boleto fica para a próxima etapa)_"
            ),
        )
