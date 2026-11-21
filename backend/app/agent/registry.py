"""Registro automático de plugins via decorator."""
from app.agent.base import BasePlugin

PLUGIN_REGISTRY: dict[str, BasePlugin] = {}


def register_plugin(cls: type[BasePlugin]) -> type[BasePlugin]:
    instancia = cls()
    PLUGIN_REGISTRY[instancia.name] = instancia
    return cls


def plugins_para_perfil(perfil: str) -> list[BasePlugin]:
    return [p for p in PLUGIN_REGISTRY.values() if perfil in p.allowed_roles]


def get_plugin(nome: str) -> BasePlugin | None:
    return PLUGIN_REGISTRY.get(nome)
