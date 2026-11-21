from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.cliente import Cliente
from app.services import financeiro as svc
from app.services import whatsapp as wsvc


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

        # Envio automático do boleto por WhatsApp (gatilho transacional)
        aviso = ""
        if cliente.telefone and not cliente.whatsapp_opt_out:
            texto = wsvc.render_template(
                "boleto",
                {"nome": cliente.nome.split()[0], "valor": f"{float(valor):.2f}", "data": venc.strftime("%d/%m/%Y")},
            )
            if transacao.boleto_url:
                texto += f"\n{transacao.boleto_url}"
            msg = await wsvc.disparar(
                context.db, cliente, texto, gatilho="boleto", processo_id=params.get("processo_id")
            )
            if msg:
                aviso = " Aviso enviado ao cliente por WhatsApp." if msg.status == "aprovada" else " Aviso de WhatsApp aguardando confirmação."

        return PluginResult(
            success=True,
            data={"transacao_id": transacao.id, "boleto_url": transacao.boleto_url},
            display=(
                f"🧾 Boleto gerado para **{cliente.nome}**: R$ {float(valor):.2f}, "
                f"vence {venc.strftime('%d/%m/%Y')}.{aviso}"
            ),
        )
