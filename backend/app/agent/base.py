"""Contratos base do sistema de plugins (plugguinhos) do Cláudio."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario


@dataclass
class Action:
    """Botão de ação sugerido ao usuário."""
    label: str
    plugin: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    ok: bool
    erro: str | None = None


@dataclass
class AgentContext:
    """Contexto de execução de um turno do agente."""
    user: Usuario
    db: AsyncSession
    mensagem: str
    historico: list[dict[str, str]] = field(default_factory=list)
    scope_filter: dict[str, Any] = field(default_factory=dict)
    read_only: bool = False


@dataclass
class PluginResult:
    success: bool
    data: dict[str, Any] | None = None
    display: str | None = None
    actions: list[Action] = field(default_factory=list)
    error: str | None = None


class BasePlugin(ABC):
    name: str
    description: str
    parameters: dict[str, Any] = {}
    requires_confirmation: bool = False
    allowed_roles: list[str] = ["socio", "advogado", "estagiario", "financeiro"]

    async def validate(self, params: dict[str, Any]) -> ValidationResult:
        for campo, spec in self.parameters.items():
            if spec.get("required") and campo not in params:
                return ValidationResult(False, f"Parâmetro obrigatório ausente: {campo}")
        return ValidationResult(True)

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: AgentContext) -> PluginResult:
        ...
