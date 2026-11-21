"""Webhook de pagamentos (gateway/banco): dá baixa automática e identifica o pagador."""
import logging

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.integrations.pagamentos import parse_webhook
from app.models.cliente import Cliente
from app.models.notificacao import Notificacao
from app.models.processo import Processo
from app.services import conciliacao
from sqlalchemy import select

logger = logging.getLogger("claudio.pagamentos.api")
router = APIRouter(prefix="/api/pagamentos", tags=["pagamentos"])


@router.post("/webhook")
async def webhook(payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Recebe a notificação de pagamento. Público (o gateway chama direto)."""
    dados = parse_webhook(payload)
    if not dados:
        return {"ignorado": "evento não é de pagamento"}

    resultado = await conciliacao.registrar_pagamento(
        db, dados["referencia"], dados["valor"], dados["pagador"], dados["data_pagamento"]
    )

    # Notifica o advogado do processo vinculado (quando conciliado)
    cliente_id = resultado.get("cliente_id")
    if cliente_id:
        proc = (
            await db.execute(select(Processo).where(Processo.cliente_id == cliente_id).limit(1))
        ).scalar_one_or_none()
        if proc and proc.advogado_id:
            cliente = await db.get(Cliente, cliente_id)
            db.add(
                Notificacao(
                    usuario_id=proc.advogado_id,
                    processo_id=proc.id,
                    tipo="sistema",
                    titulo="Pagamento recebido",
                    corpo=f"Baixa automática do boleto de {cliente.nome if cliente else 'cliente'} "
                    f"(R$ {dados['valor']}).",
                )
            )
    return {"status": "processado", **resultado}
