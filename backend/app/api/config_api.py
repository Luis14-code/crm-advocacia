"""Configurações de integrações do escritório (acesso do sócio)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.database import get_db
from app.integrations import datajud
from app.models.enums import Perfil
from app.models.usuario import Usuario
from app.schemas.config import (
    IntegracoesStatus,
    IntegracoesUpdate,
    TestarDataJud,
    TesteResultado,
)
from app.services import configuracoes as cfg

router = APIRouter(prefix="/api/config", tags=["config"])

_socio = require_roles(Perfil.socio)


async def _montar_status(db: AsyncSession) -> IntegracoesStatus:
    _, fonte = await cfg.get_datajud_api_key(db)
    jus = await cfg.get_jusbrasil_default_token(db)
    wa = await cfg.get_waakg_config(db)
    return IntegracoesStatus(
        datajud_configurada=(fonte != "publico"),
        datajud_fonte=fonte,
        jusbrasil_configurado=bool(jus),
        waakg_configurado=bool(wa.get("api_key")),
        waakg_base_url=wa.get("base_url"),
        waakg_session_id=wa.get("session_id"),
    )


@router.get("/integracoes", response_model=IntegracoesStatus)
async def status_integracoes(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(_socio)
):
    return await _montar_status(db)


@router.put("/integracoes", response_model=IntegracoesStatus)
async def salvar_integracoes(
    body: IntegracoesUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_socio),
):
    if body.datajud_api_key is not None:
        await cfg.definir(
            db, cfg.DATAJUD_API_KEY, body.datajud_api_key.strip(),
            secreto=True, descricao="API key do DataJud (CNJ)",
        )
    if body.jusbrasil_default_token is not None:
        await cfg.definir(
            db, cfg.JUSBRASIL_DEFAULT_TOKEN, body.jusbrasil_default_token.strip(),
            secreto=True, descricao="Token padrão do JusBrasil (fallback)",
        )
    if body.waakg_base_url is not None:
        await cfg.definir(db, cfg.WAAKG_BASE_URL, body.waakg_base_url.strip(), descricao="URL base do WA-AKG")
    if body.waakg_api_key is not None:
        await cfg.definir(db, cfg.WAAKG_API_KEY, body.waakg_api_key.strip(), secreto=True, descricao="API key do WA-AKG")
    if body.waakg_session_id is not None:
        await cfg.definir(db, cfg.WAAKG_SESSION_ID, body.waakg_session_id.strip(), descricao="ID da sessão WA-AKG")
    await db.flush()
    return await _montar_status(db)


@router.post("/integracoes/testar-datajud", response_model=TesteResultado)
async def testar_datajud(
    body: TestarDataJud,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_socio),
):
    if body.api_key:
        chave = body.api_key.strip()
    else:
        chave, _fonte = await cfg.get_datajud_api_key(db)
    ok, detalhe = await datajud.testar_conexao(chave)
    return TesteResultado(ok=ok, detalhe=detalhe)
