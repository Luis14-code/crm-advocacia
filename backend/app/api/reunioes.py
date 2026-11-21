"""Reuniões: upload de áudio, listagem, detalhe e edição dos fatos extraídos."""
import logging
import os
import uuid

import jwt
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.core.security import decodificar_token
from app.database import get_db
from app.models.agente import Reuniao
from app.models.usuario import Usuario
from app.schemas.reuniao import FatosUpdate, ReuniaoOut, ReuniaoResumoOut

logger = logging.getLogger("claudio.reunioes")
router = APIRouter(prefix="/api/reunioes", tags=["reunioes"])

EXTENSOES_OK = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4"}


@router.get("", response_model=list[ReuniaoResumoOut])
async def listar(
    cliente_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    stmt = select(Reuniao)
    # Advogado/estagiário veem as próprias reuniões
    if user.perfil in ("advogado", "estagiario"):
        stmt = stmt.where(Reuniao.advogado_id == user.id)
    if cliente_id:
        stmt = stmt.where(Reuniao.cliente_id == cliente_id)
    stmt = stmt.order_by(Reuniao.created_at.desc()).limit(100)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{reuniao_id}", response_model=ReuniaoOut)
async def detalhe(
    reuniao_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    reuniao = await db.get(Reuniao, reuniao_id)
    if not reuniao:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada")
    if user.perfil in ("advogado", "estagiario") and reuniao.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso")
    return reuniao


@router.post("", response_model=ReuniaoOut, status_code=status.HTTP_201_CREATED)
async def upload(
    audio: UploadFile = File(...),
    cliente_id: int | None = Form(default=None),
    processo_id: int | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    ext = os.path.splitext(audio.filename or "")[1].lower()
    if ext not in EXTENSOES_OK:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Formato não suportado ({ext}). Aceitos: {', '.join(sorted(EXTENSOES_OK))}",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    nome = f"{uuid.uuid4().hex}{ext}"
    destino = os.path.join(settings.upload_dir, nome)

    # Salva em disco com limite de tamanho
    limite = settings.max_upload_mb * 1024 * 1024
    tamanho = 0
    with open(destino, "wb") as out:
        while True:
            chunk = await audio.read(1024 * 1024)
            if not chunk:
                break
            tamanho += len(chunk)
            if tamanho > limite:
                out.close()
                os.remove(destino)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"Áudio excede {settings.max_upload_mb} MB",
                )
            out.write(chunk)

    reuniao = Reuniao(
        cliente_id=cliente_id,
        processo_id=processo_id,
        advogado_id=user.id,
        status="pendente",
        audio_path=destino,
    )
    db.add(reuniao)
    await db.flush()
    await db.refresh(reuniao)

    # Enfileira a transcrição (fila 'whisper')
    try:
        from app.tasks.transcricao_tasks import transcrever_reuniao_task

        transcrever_reuniao_task.delay(reuniao.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Não foi possível enfileirar transcrição: %s", exc)

    return reuniao


@router.get("/{reuniao_id}/audio")
async def stream_audio(
    reuniao_id: int,
    token: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Serve o áudio da reunião. Autentica por token na query (para a tag <audio>)."""
    try:
        payload = decodificar_token(token, "access")
        usuario_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    reuniao = await db.get(Reuniao, reuniao_id)
    if not reuniao or not reuniao.audio_path or not os.path.exists(reuniao.audio_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Áudio não encontrado")

    user = await db.get(Usuario, usuario_id)
    if user and user.perfil in ("advogado", "estagiario") and reuniao.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso")

    return FileResponse(reuniao.audio_path)


@router.patch("/{reuniao_id}", response_model=ReuniaoOut)
async def editar_fatos(
    reuniao_id: int,
    body: FatosUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    reuniao = await db.get(Reuniao, reuniao_id)
    if not reuniao:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reunião não encontrada")
    if user.perfil in ("advogado", "estagiario") and reuniao.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso")

    dados = body.model_dump(exclude_unset=True)
    if "fatos_peticao" in dados:
        reuniao.fatos_peticao = dados["fatos_peticao"]
    if "pendencias" in dados:
        reuniao.pendencias = dados["pendencias"]
    if "resumo" in dados and dados["resumo"] is not None:
        reuniao.resumo = dados["resumo"]
    await db.flush()
    await db.refresh(reuniao)
    return reuniao
