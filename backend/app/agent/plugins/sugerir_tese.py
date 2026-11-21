from typing import Any

from sqlalchemy import func, select

from app.agent.base import AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.agente import ResultadoCaso
from app.models.processo import Processo
from app.services import teses as svc_teses


@register_plugin
class SugerirTesePlugin(BasePlugin):
    name = "sugerir_tese"
    description = "Sugere teses jurídicas pertinentes ao tipo do processo, com apoio da jurimetria interna."
    parameters = {
        "processo_id": {"type": "integer", "required": False},
        "tipo": {"type": "string", "required": False},
        "subtipo": {"type": "string", "required": False},
    }
    requires_confirmation = False
    allowed_roles = ["socio", "advogado"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        tipo = params.get("tipo")
        subtipo = params.get("subtipo")
        contexto_proc = None

        processo_id = params.get("processo_id")
        if processo_id:
            proc = await context.db.get(Processo, int(processo_id))
            if proc:
                tipo = tipo or proc.tipo
                subtipo = subtipo or proc.subtipo
                contexto_proc = proc.numero

        teses = svc_teses.sugerir(tipo, subtipo)
        linhas = [f"{i}. {t}" for i, t in enumerate(teses, 1)]

        titulo = "💡 **Teses sugeridas**"
        if contexto_proc:
            titulo += f" — processo {contexto_proc}"
        elif tipo:
            titulo += f" — {tipo}" + (f"/{subtipo}" if subtipo else "")

        # Enriquecimento com jurimetria interna (se houver histórico)
        jurimetria = ""
        if tipo:
            stats = (
                await context.db.execute(
                    select(
                        ResultadoCaso.resultado, func.count().label("n")
                    )
                    .join(Processo, ResultadoCaso.processo_id == Processo.id)
                    .where(Processo.tipo == tipo)
                    .group_by(ResultadoCaso.resultado)
                )
            ).all()
            if stats:
                total = sum(n for _, n in stats)
                partes = [f"{r}: {round(100 * n / total)}%" for r, n in stats if r]
                if partes:
                    jurimetria = (
                        f"\n\n📈 Histórico do escritório em '{tipo}' ({total} casos): "
                        + ", ".join(partes)
                    )

        return PluginResult(
            success=True,
            data={"teses": teses},
            display=f"{titulo}\n" + "\n".join(linhas) + jurimetria,
        )
