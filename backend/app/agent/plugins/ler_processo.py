from typing import Any

from sqlalchemy import select

from app.agent.base import Action, AgentContext, BasePlugin, PluginResult
from app.agent.registry import register_plugin
from app.integrations.datajud import normalizar_numero
from app.models.enums import Perfil
from app.models.movimentacao import Movimentacao
from app.models.prazo import Prazo
from app.models.processo import Processo
from app.services import sync


@register_plugin
class LerProcessoPlugin(BasePlugin):
    name = "ler_processo"
    description = "Lê e resume um processo judicial pelo número CNJ (movimentações, prazos, brechas)."
    parameters = {"numero": {"type": "string", "required": True, "description": "Número CNJ"}}
    requires_confirmation = False
    allowed_roles = ["socio", "advogado", "estagiario", "financeiro"]

    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        numero = (params.get("numero") or "").strip()
        if not numero:
            return PluginResult(success=False, display="Me informe o número do processo (CNJ).")

        alvo = normalizar_numero(numero)
        processos = (await context.db.execute(select(Processo))).scalars().all()
        processo = next((p for p in processos if normalizar_numero(p.numero) == alvo), None)

        if not processo:
            return PluginResult(
                success=True,
                display=f"Não encontrei o processo {numero} no sistema. Cadastre-o primeiro.",
            )

        # Escopo por perfil
        if (
            context.user.perfil in (Perfil.advogado.value, Perfil.estagiario.value)
            and processo.advogado_id != context.user.id
        ):
            return PluginResult(success=False, display="Você não tem acesso a esse processo.")

        # Atualiza do DataJud (tolerante a falha)
        fonte = None
        try:
            r = await sync.sincronizar_processo(context.db, processo)
            fonte = r.get("fonte")
        except Exception:  # noqa: BLE001
            fonte = "parcial"

        movs = (
            await context.db.execute(
                select(Movimentacao)
                .where(Movimentacao.processo_id == processo.id)
                .order_by(Movimentacao.data.desc())
                .limit(5)
            )
        ).scalars().all()
        prazos = (
            await context.db.execute(
                select(Prazo)
                .where(Prazo.processo_id == processo.id, Prazo.status == "pendente")
                .order_by(Prazo.data_limite_util)
            )
        ).scalars().all()

        partes = [
            f"⚖️ **Processo {processo.numero}**",
            f"Tipo: {processo.tipo}" + (f" / {processo.subtipo}" if processo.subtipo else ""),
            f"Status: {processo.status}" + (f" · Vara: {processo.vara}" if processo.vara else ""),
        ]
        if processo.tese_principal:
            partes.append(f"Tese: {processo.tese_principal}")

        if movs:
            partes.append("\n**Últimas movimentações:**")
            partes += [f"• {m.data.strftime('%d/%m/%Y')} — {m.descricao}" for m in movs]
        else:
            partes.append("\n_Sem movimentações registradas._")

        if prazos:
            partes.append("\n**Prazos pendentes:**")
            partes += [
                f"• {p.data_limite_util.strftime('%d/%m/%Y')} — {p.descricao}" for p in prazos
            ]

        if fonte == "parcial":
            partes.append("\n_(sincronização parcial — DataJud indisponível no momento)_")

        return PluginResult(
            success=True,
            data={"processo_id": processo.id, "movimentacoes": len(movs), "prazos": len(prazos)},
            display="\n".join(partes),
            actions=[
                Action(label="Ver prazos", plugin="verificar_prazos"),
                Action(label="Sugerir tese", plugin="sugerir_tese", params={"processo_id": processo.id}),
            ],
        )
