"""Endpoint WebSocket do chat com o Cláudio."""
import logging
from dataclasses import asdict

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.agent.base import AgentContext
from app.agent.core import processar_mensagem, salvar_mensagem
from app.core.security import decodificar_token
from app.database import async_session_factory
from app.models.usuario import Usuario

logger = logging.getLogger("claudio.ws")
router = APIRouter()


@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket, token: str = ""):
    # Autentica via token na query string (?token=...)
    try:
        payload = decodificar_token(token, "access")
        usuario_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            dados = await websocket.receive_json()
            texto = (dados.get("mensagem") or "").strip()
            historico = dados.get("historico") or []
            if not texto:
                continue

            async with async_session_factory() as db:
                usuario = await db.get(Usuario, usuario_id)
                if not usuario or not usuario.ativo:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return

                context = AgentContext(
                    user=usuario, db=db, mensagem=texto, historico=historico
                )
                await salvar_mensagem(context, "user", texto)
                resultado = await processar_mensagem(context)
                await salvar_mensagem(
                    context, "assistant", resultado.display or "", meta=resultado.data
                )
                await db.commit()

            await websocket.send_json(
                {
                    "success": resultado.success,
                    "display": resultado.display,
                    "data": resultado.data,
                    "actions": [asdict(a) for a in resultado.actions],
                    "error": resultado.error,
                }
            )
    except WebSocketDisconnect:
        logger.info("WS desconectado: usuário %s", usuario_id)
    except Exception:  # noqa: BLE001
        logger.exception("Erro no WS do chat")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
