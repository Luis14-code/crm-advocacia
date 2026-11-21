"""Cache simples em Redis para endpoints pesados (jurimetria, dashboard do dono).

Degrada graciosamente: se o Redis estiver indisponível, apenas executa a função.
"""
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("claudio.cache")

_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis | None:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis indisponível para cache: %s", exc)
            return None
    return _redis


async def cached_json(chave: str, ttl: int, produtor: Callable[[], Awaitable[Any]]) -> Any:
    r = _get_redis()
    if r is not None:
        try:
            bruto = await r.get(chave)
            if bruto:
                return json.loads(bruto)
        except Exception:  # noqa: BLE001
            r = None  # cai para execução direta

    dados = await produtor()

    if r is not None:
        try:
            await r.set(chave, json.dumps(dados, default=str), ex=ttl)
        except Exception:  # noqa: BLE001
            pass
    return dados


async def invalidar(prefixo: str) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        async for chave in r.scan_iter(f"{prefixo}*"):
            await r.delete(chave)
    except Exception:  # noqa: BLE001
        pass
