"""Módulo financeiro — exige perfil (sócio/financeiro) E token sensível."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_sensitive
from app.database import get_db
from app.models.financeiro import Transacao
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.financeiro import (
    GerarBoletoRequest,
    SimularAcordoRequest,
    TransacaoCreate,
    TransacaoOut,
    TransacaoUpdate,
)
from app.services import financeiro as svc

router = APIRouter(prefix="/api/financeiro", tags=["financeiro"])

PERFIS_FINANCEIRO = {"socio", "financeiro"}


async def acesso_financeiro(user: Usuario = Depends(require_sensitive)) -> Usuario:
    """Exige token sensível (via require_sensitive) + perfil sócio/financeiro."""
    if user.perfil not in PERFIS_FINANCEIRO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso restrito ao financeiro")
    return user


@router.get("/transacoes", response_model=list[TransacaoOut])
async def listar(
    inicio: date | None = None,
    fim: date | None = None,
    categoria: str | None = None,
    tipo: str | None = None,
    status_: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    stmt = select(Transacao)
    if inicio:
        stmt = stmt.where(Transacao.data_vencimento >= inicio)
    if fim:
        stmt = stmt.where(Transacao.data_vencimento <= fim)
    if categoria:
        stmt = stmt.where(Transacao.categoria == categoria)
    if tipo:
        stmt = stmt.where(Transacao.tipo == tipo)
    if status_:
        stmt = stmt.where(Transacao.status == status_)
    stmt = stmt.order_by(Transacao.data_vencimento.desc().nullslast()).limit(500)
    return (await db.execute(stmt)).scalars().all()


@router.post("/transacoes", response_model=TransacaoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: TransacaoCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    transacao = Transacao(**body.model_dump())
    db.add(transacao)
    await db.flush()
    await db.refresh(transacao)
    return transacao


@router.put("/transacoes/{transacao_id}", response_model=TransacaoOut)
async def atualizar(
    transacao_id: int,
    body: TransacaoUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    t = await db.get(Transacao, transacao_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transação não encontrada")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(t, campo, valor)
    await db.flush()
    await db.refresh(t)
    return t


@router.post("/simular-acordo")
async def simular(
    body: SimularAcordoRequest,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    processo = await db.get(Processo, body.processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    return await svc.simular_acordo(db, processo, body.valor_bruto, body.parcelas)


@router.get("/fluxo-caixa")
async def fluxo_caixa(
    inicio: date,
    fim: date,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    return await svc.fluxo_caixa(db, inicio, fim)


@router.get("/relatorio")
async def relatorio(
    inicio: date,
    fim: date,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    return await svc.relatorio_periodo(db, inicio, fim)


@router.post("/boleto", response_model=TransacaoOut, status_code=status.HTTP_201_CREATED)
async def gerar_boleto(
    body: GerarBoletoRequest,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    transacao = await svc.gerar_boleto(
        db, body.cliente_id, body.valor, body.vencimento, body.processo_id, body.descricao
    )
    # Envio por WhatsApp (se solicitado) é tratado pelo módulo WhatsApp com confirmação.
    return transacao
