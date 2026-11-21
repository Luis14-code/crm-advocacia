from typing import Any

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.cliente import Cliente
from app.services import whatsapp as svc


@register_plugin
class EnviarWhatsappPlugin(BasePlugin):
    name = "enviar_whatsapp"
    description = "Prepara uma mensagem de WhatsApp para um cliente (fica aguardando sua confirmação)."
    parameters = {
        "cliente_id": {"type": "integer", "required": True},
        "texto": {"type": "string", "required": True},
        "processo_id": {"type": "integer", "required": False},
    }
    requires_confirmation = True
    allowed_roles = ["socio", "advogado", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        cliente_id = params.get("cliente_id")
        texto = (params.get("texto") or "").strip()
        if not cliente_id or not texto:
            return PluginResult(success=False, display="Preciso do cliente e do texto da mensagem.")

        cliente = await context.db.get(Cliente, int(cliente_id))
        if not cliente:
            return PluginResult(success=False, display="Cliente não encontrado.")

        msg = await svc.criar_pendente(
            context.db, cliente, texto, gatilho="manual",
            usuario_id=context.user.id, processo_id=params.get("processo_id"),
        )
        if msg is None:
            return PluginResult(
                success=False,
                display=f"{cliente.nome} não tem telefone cadastrado ou optou por não receber WhatsApp.",
            )
        return PluginResult(
            success=True,
            data={"mensagem_id": msg.id},
            display=(
                f"📱 Mensagem para **{cliente.nome}** criada e **aguardando sua confirmação** "
                "na tela de WhatsApp:\n\n"
                f"> {texto}\n\n_Nada é enviado até você aprovar._"
            ),
        )
