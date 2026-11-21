"""Orquestrador do Cláudio: classifica intenção, executa plugin, audita e responde."""
import logging
import time
from dataclasses import asdict

from app.agent import plugins as _plugins  # noqa: F401  (dispara auto-registro)
from app.agent.base import AgentContext, PluginResult
from app.agent.llm import classificar_intencao
from app.agent.registry import get_plugin, plugins_para_perfil
from app.models.agente import AuditLog, Mensagem

logger = logging.getLogger("claudio.agent")

MAX_PLUGIN_CALLS = 5


def _descricao_plugins(perfil: str) -> str:
    return "\n".join(
        f"- {p.name}: {p.description}" for p in plugins_para_perfil(perfil)
    )


def _roteamento_heuristico(mensagem: str) -> tuple[str, dict] | None:
    """Fallback simples por palavras-chave quando o LLM está indisponível."""
    m = mensagem.lower()
    if any(t in m for t in ["processo", "processos", "casos", "meus process"]):
        params = {}
        if "encerrad" in m:
            params["status"] = "encerrado"
        elif "arquivad" in m:
            params["status"] = "arquivado"
        return "listar_processos", params
    if any(t in m for t in ["cliente", "cpf", "quem é", "contato"]):
        # extrai um possível termo após a palavra "cliente"
        return "buscar_cliente", {"termo": mensagem}
    if any(t in m for t in ["ajuda", "o que você faz", "o que voce faz", "pode fazer", "help", "comandos"]):
        return "ajuda", {}
    return None


async def processar_mensagem(context: AgentContext) -> PluginResult:
    """Processa um turno e retorna o PluginResult para o frontend."""
    perfil = context.user.perfil

    # 1) Classificação de intenção (LLM, com fallback heurístico)
    intencao = await classificar_intencao(context.mensagem, _descricao_plugins(perfil))
    escolha: tuple[str, dict] | None = None
    if intencao and intencao.get("plugin"):
        escolha = (intencao["plugin"], intencao.get("params") or {})
    if escolha is None:
        escolha = _roteamento_heuristico(context.mensagem)

    # 2) Nenhum plugin aplicável → resposta genérica
    if escolha is None:
        return PluginResult(
            success=True,
            display=(
                "Ainda não sei fazer isso. Digite **ajuda** para ver o que eu "
                "consigo fazer por enquanto."
            ),
        )

    nome_plugin, params = escolha
    plugin = get_plugin(nome_plugin)

    if plugin is None:
        return PluginResult(success=False, error="Plugin inexistente", display="Não entendi o pedido.")

    # 3) Autorização por perfil
    if perfil not in plugin.allowed_roles:
        return PluginResult(
            success=False,
            error="forbidden",
            display=f"Seu perfil ({perfil}) não tem acesso a essa função.",
        )

    # 4) Validação de parâmetros
    validacao = await plugin.validate(params)
    if not validacao.ok:
        return PluginResult(success=False, error=validacao.erro, display=validacao.erro)

    # 5) Execução com auditoria
    inicio = time.perf_counter()
    try:
        resultado = await plugin.execute(params, context)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro no plugin %s", nome_plugin)
        resultado = PluginResult(
            success=False, error=str(exc), display="Tive um problema ao executar isso."
        )
    duracao_ms = int((time.perf_counter() - inicio) * 1000)

    await _auditar(context, nome_plugin, params, resultado, duracao_ms)
    return resultado


async def _auditar(
    context: AgentContext,
    plugin: str,
    params: dict,
    resultado: PluginResult,
    duracao_ms: int,
) -> None:
    try:
        context.db.add(
            AuditLog(
                usuario_id=context.user.id,
                acao="plugin_execucao",
                plugin=plugin,
                parametros=params,
                resultado={"display": resultado.display, "data": resultado.data},
                sucesso=resultado.success,
                duracao_ms=duracao_ms,
            )
        )
    except Exception:  # noqa: BLE001
        logger.warning("Falha ao gravar audit_log")


async def salvar_mensagem(context: AgentContext, role: str, conteudo: str, meta: dict | None = None):
    context.db.add(
        Mensagem(usuario_id=context.user.id, role=role, conteudo=conteudo, meta=meta)
    )
