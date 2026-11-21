"""WhatsApp (WA-AKG): conexão/QR, envio com confirmação, histórico e webhook."""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.integrations.waakg import WaakgError
from app.models.cliente import Cliente
from app.models.enums import Perfil
from app.models.notificacao import Notificacao
from app.models.usuario import Usuario
from app.models.whatsapp import MensagemWhatsapp
from app.schemas.whatsapp import (
    EnviarWhatsappRequest,
    MensagemWhatsappOut,
    StatusWhatsapp,
)
from app.services import configuracoes as cfg
from app.services import whatsapp as svc

logger = logging.getLogger("claudio.whatsapp.api")
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

_socio = require_roles(Perfil.socio)
_pode_enviar = require_roles(Perfil.socio, Perfil.advogado, Perfil.financeiro)


@router.get("/status", response_model=StatusWhatsapp)
async def status_conexao(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(get_current_user)
):
    client = await svc.cliente_waakg(db)
    if client is None:
        return StatusWhatsapp(configurado=False, conectado=False, detalhe="Gateway não configurado")
    try:
        info = await client.status()
        data = info.get("data") or info
        estado = str(data.get("status", "")).lower()
        return StatusWhatsapp(
            configurado=True,
            conectado=estado == "connected",
            detalhe=data.get("status"),
            telefone=(data.get("me") or {}).get("id") if isinstance(data.get("me"), dict) else None,
        )
    except WaakgError as exc:
        return StatusWhatsapp(configurado=True, conectado=False, detalhe=str(exc))


@router.post("/conectar")
async def conectar(db: AsyncSession = Depends(get_db), _: Usuario = Depends(_socio)):
    client = await svc.cliente_waakg(db)
    if client is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Configure a API key do WA-AKG primeiro")
    try:
        await client.criar_sessao("Cláudio")
    except WaakgError:
        pass  # sessão pode já existir
    try:
        await client.iniciar()
    except WaakgError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return {"status": "iniciando", "detalhe": "Abra o QR para parear o número."}


@router.get("/qr")
async def obter_qr(db: AsyncSession = Depends(get_db), _: Usuario = Depends(_socio)):
    client = await svc.cliente_waakg(db)
    if client is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Gateway não configurado")
    try:
        info = await client.obter_qr()
        data = info.get("data") or info
        return {"base64": data.get("base64"), "qr": data.get("qr")}
    except WaakgError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"QR indisponível: {exc}")


@router.get("/mensagens", response_model=list[MensagemWhatsappOut])
async def historico(
    cliente_id: int | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = select(MensagemWhatsapp)
    if cliente_id:
        stmt = stmt.where(MensagemWhatsapp.cliente_id == cliente_id)
    if status_:
        stmt = stmt.where(MensagemWhatsapp.status == status_)
    stmt = stmt.order_by(MensagemWhatsapp.created_at.desc()).limit(200)
    return (await db.execute(stmt)).scalars().all()


@router.get("/pendentes", response_model=list[MensagemWhatsappOut])
async def pendentes(
    db: AsyncSession = Depends(get_db), user: Usuario = Depends(get_current_user)
):
    stmt = select(MensagemWhatsapp).where(
        MensagemWhatsapp.direcao == "saida",
        MensagemWhatsapp.status == "aguardando_confirmacao",
    )
    if user.perfil in (Perfil.advogado.value, Perfil.estagiario.value):
        stmt = stmt.where(MensagemWhatsapp.usuario_id == user.id)
    return (await db.execute(stmt.order_by(MensagemWhatsapp.created_at.desc()))).scalars().all()


@router.post("/enviar", response_model=MensagemWhatsappOut, status_code=status.HTTP_201_CREATED)
async def enviar(
    body: EnviarWhatsappRequest,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(_pode_enviar),
):
    cliente = await db.get(Cliente, body.cliente_id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

    texto = body.texto
    if body.template:
        ctx = {"nome": cliente.nome.split()[0], **(body.contexto or {})}
        texto = svc.render_template(body.template, ctx)
    if not texto:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe 'texto' ou 'template'")

    auto = body.auto_aprovar and user.perfil == Perfil.socio.value
    msg = await svc.criar_pendente(
        db, cliente, texto, gatilho="manual", usuario_id=user.id,
        processo_id=body.processo_id, auto_aprovar=auto,
    )
    if msg is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Cliente sem telefone ou com opt-out de WhatsApp",
        )
    await db.flush()
    if auto:
        from app.tasks.whatsapp_tasks import enviar_whatsapp_task

        await db.commit()
        enviar_whatsapp_task.delay(msg.id)
    await db.refresh(msg)
    return msg


@router.post("/{mensagem_id}/aprovar", response_model=MensagemWhatsappOut)
async def aprovar(
    mensagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(_pode_enviar),
):
    msg = await db.get(MensagemWhatsapp, mensagem_id)
    if not msg or msg.direcao != "saida":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mensagem não encontrada")
    if msg.status != "aguardando_confirmacao":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Mensagem já está '{msg.status}'")
    msg.status = "aprovada"
    await db.commit()

    from app.tasks.whatsapp_tasks import enviar_whatsapp_task

    enviar_whatsapp_task.delay(msg.id)
    await db.refresh(msg)
    return msg


@router.post("/{mensagem_id}/rejeitar", response_model=MensagemWhatsappOut)
async def rejeitar(
    mensagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(_pode_enviar),
):
    msg = await db.get(MensagemWhatsapp, mensagem_id)
    if not msg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mensagem não encontrada")
    msg.status = "rejeitada"
    await db.flush()
    await db.refresh(msg)
    return msg


@router.post("/webhook")
async def webhook(payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Recebe mensagens do WA-AKG (evento message.received). Público (sem auth de usuário)."""
    data = payload.get("data") or {}
    if data.get("fromMe"):
        return {"ignorado": "fromMe"}
    remetente = data.get("sender") or data.get("from") or ""
    telefone = remetente.split("@")[0] if remetente else None
    conteudo = data.get("content")
    if isinstance(conteudo, dict):
        conteudo = conteudo.get("text") or str(conteudo)
    if not telefone or not conteudo:
        return {"ignorado": "payload incompleto"}

    # Tenta casar o cliente pelo final do telefone
    clientes = (await db.execute(select(Cliente))).scalars().all()
    so_digitos = "".join(c for c in telefone if c.isdigit())
    cliente = next(
        (c for c in clientes if c.telefone and "".join(d for d in c.telefone if d.isdigit())[-8:] == so_digitos[-8:]),
        None,
    )

    db.add(
        MensagemWhatsapp(
            cliente_id=cliente.id if cliente else None,
            direcao="entrada",
            telefone=telefone,
            texto=str(conteudo)[:4000],
            gatilho="recebida",
            status="recebida",
        )
    )
    # Notifica o advogado responsável, se houver cliente
    if cliente:
        from app.models.processo import Processo

        proc = (
            await db.execute(
                select(Processo).where(Processo.cliente_id == cliente.id).limit(1)
            )
        ).scalar_one_or_none()
        if proc and proc.advogado_id:
            db.add(
                Notificacao(
                    usuario_id=proc.advogado_id,
                    processo_id=proc.id,
                    tipo="sistema",
                    titulo=f"WhatsApp de {cliente.nome}",
                    corpo=str(conteudo)[:200],
                )
            )
    return {"status": "recebida"}
