from typing import Any

from sqlalchemy import select

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.agente import Reuniao


@register_plugin
class TranscreverReuniaoPlugin(BasePlugin):
    name = "transcrever_reuniao"
    description = "Mostra o resultado processado de uma reunião (resumo, fatos, pendências) ou seu status."
    parameters = {
        "reuniao_id": {"type": "integer", "required": False},
        "cliente_id": {"type": "integer", "required": False},
    }
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        reuniao = None
        if params.get("reuniao_id"):
            reuniao = await context.db.get(Reuniao, int(params["reuniao_id"]))
        else:
            stmt = select(Reuniao).order_by(Reuniao.created_at.desc())
            if params.get("cliente_id"):
                stmt = stmt.where(Reuniao.cliente_id == int(params["cliente_id"]))
            if context.user.perfil in ("advogado", "estagiario"):
                stmt = stmt.where(Reuniao.advogado_id == context.user.id)
            reuniao = (await context.db.execute(stmt.limit(1))).scalar_one_or_none()

        if not reuniao:
            return PluginResult(
                success=True,
                display="Não encontrei reuniões. Faça o upload de um áudio na tela de Reuniões.",
            )

        if reuniao.status != "concluido":
            return PluginResult(
                success=True,
                display=f"A reunião #{reuniao.id} está com status **{reuniao.status}**. "
                "Assim que a transcrição concluir, te mostro o resumo e os fatos.",
            )

        partes = [f"🎙️ **Reunião #{reuniao.id}** — {reuniao.duracao_segundos or 0}s", ""]
        if reuniao.resumo:
            partes += ["**Resumo:**", reuniao.resumo, ""]
        fatos = reuniao.fatos_peticao or []
        if fatos:
            partes += ["**Fatos para petição:**"] + [f"• {f}" for f in fatos] + [""]
        pend = reuniao.pendencias or []
        if pend:
            partes += ["**Pendências:**"] + [f"• {p}" for p in pend]

        return PluginResult(
            success=True,
            data={"reuniao_id": reuniao.id, "fatos": fatos},
            display="\n".join(partes),
        )
