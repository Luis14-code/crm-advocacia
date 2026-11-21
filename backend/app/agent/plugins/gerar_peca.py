from typing import Any

from app.agent.base import Action, AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.models.cliente import Cliente
from app.models.documento import Documento
from app.models.enums import Perfil
from app.models.processo import Processo
from app.services import embeddings, pecas


@register_plugin
class GerarPecaPlugin(BasePlugin):
    name = "gerar_peca"
    description = "Gera uma minuta de peça processual (petição inicial, contestação, recurso) para um processo."
    parameters = {
        "processo_id": {"type": "integer", "required": False},
        "tipo": {"type": "string", "required": False, "enum": list(pecas.TIPOS.keys())},
        "fatos": {"type": "array", "required": False},
    }
    requires_confirmation = True
    allowed_roles = ["socio", "advogado"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        processo_id = params.get("processo_id")
        if not processo_id:
            return PluginResult(
                success=False,
                display="Para qual processo devo gerar a peça? Me diga o processo (ex: pelo número).",
            )

        processo = await context.db.get(Processo, int(processo_id))
        if not processo:
            return PluginResult(success=False, display="Processo não encontrado.")
        if context.user.perfil == Perfil.advogado.value and processo.advogado_id != context.user.id:
            return PluginResult(success=False, display="Você não tem acesso a esse processo.")

        tipo = params.get("tipo") or "peticao_inicial"
        cliente = (
            await context.db.get(Cliente, processo.cliente_id) if processo.cliente_id else None
        )
        fatos = [f for f in (params.get("fatos") or []) if isinstance(f, str)]

        conteudo = await pecas.gerar_peca(tipo, processo, cliente, fatos)
        doc = Documento(
            processo_id=processo.id,
            autor_id=context.user.id,
            tipo=tipo,
            titulo=f"{pecas.TIPOS.get(tipo, 'Peça')} — {processo.numero}",
            conteudo=conteudo,
            gerado_por_ia=True,
        )
        context.db.add(doc)
        await context.db.flush()
        await embeddings.indexar(
            context.db, "documento", doc.id, conteudo,
            metadata={"processo_id": processo.id, "tipo": tipo},
        )

        previa = conteudo[:600] + ("..." if len(conteudo) > 600 else "")
        return PluginResult(
            success=True,
            data={"documento_id": doc.id, "tipo": tipo},
            display=f"✍️ Gerei a minuta (**{pecas.TIPOS.get(tipo, 'Peça')}**, doc #{doc.id}):\n\n{previa}\n\n"
            "_Abra em Peças para revisar, editar e exportar em PDF._",
            actions=[Action(label="Revisar documento", plugin="revisar_documento", params={"documento_id": doc.id})],
        )
