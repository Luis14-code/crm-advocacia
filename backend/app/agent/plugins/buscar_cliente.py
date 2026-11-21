from typing import Any

from sqlalchemy import or_, select

from app.agent.base import Action, AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.cliente import Cliente


@register_plugin
class BuscarClientePlugin(BasePlugin):
    name = "buscar_cliente"
    description = "Busca um cliente do escritório por nome (parcial) ou CPF."
    parameters = {
        "termo": {"type": "string", "required": True, "description": "Nome ou CPF"},
    }
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        termo = (params.get("termo") or "").strip()
        if not termo:
            return PluginResult(
                success=False,
                error="Preciso de um nome ou CPF para buscar.",
                display="Sobre qual cliente você quer saber? Me diga o nome ou CPF.",
            )

        like = f"%{termo}%"
        stmt = (
            select(Cliente)
            .where(or_(Cliente.nome.ilike(like), Cliente.cpf.ilike(like)))
            .order_by(Cliente.nome)
            .limit(10)
        )
        clientes = (await context.db.execute(stmt)).scalars().all()

        if not clientes:
            return PluginResult(
                success=True,
                display=f"Não encontrei nenhum cliente para '{termo}'.",
            )

        if len(clientes) == 1:
            c = clientes[0]
            partes = [f"**{c.nome}**"]
            if c.cpf:
                partes.append(f"CPF: {c.cpf}")
            if c.telefone:
                partes.append(f"Tel: {c.telefone}")
            if c.email:
                partes.append(f"E-mail: {c.email}")
            return PluginResult(
                success=True,
                data={"cliente_id": c.id, "nome": c.nome},
                display="\n".join(partes),
                actions=[Action(label="Ver processos", plugin="listar_processos")],
            )

        linhas = [f"• {c.nome}" + (f" (CPF {c.cpf})" if c.cpf else "") for c in clientes]
        return PluginResult(
            success=True,
            data={"total": len(clientes)},
            display=f"Encontrei {len(clientes)} clientes:\n" + "\n".join(linhas),
        )
