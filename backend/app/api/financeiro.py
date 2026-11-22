"""Módulo financeiro — exige perfil (sócio/financeiro) E token sensível."""
import asyncio
import json
from datetime import date

import jwt
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_sensitive
from app.core.security import decodificar_token
from app.database import async_session_factory, get_db
from app.models.cliente import Cliente
from app.models.cobranca import CobrancaProgramada
from app.models.financeiro import Transacao
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.financeiro import (
    CobrancaCreate,
    CobrancaOut,
    CobrancaUpdate,
    GerarBoletoRequest,
    SimularAcordoRequest,
    TransacaoCreate,
    TransacaoOut,
    TransacaoUpdate,
)
from app.services import conciliacao, financeiro as svc
from app.services import whatsapp as wsvc

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
    # Envio automático do boleto por WhatsApp (gatilho transacional, sem pré-aprovação).
    if body.enviar_whatsapp:
        cliente = await db.get(Cliente, body.cliente_id)
        if cliente and cliente.telefone and not cliente.whatsapp_opt_out:
            texto = wsvc.render_template(
                "boleto",
                {
                    "nome": cliente.nome.split()[0],
                    "valor": f"{float(body.valor):.2f}",
                    "data": body.vencimento.strftime("%d/%m/%Y"),
                },
            )
            if transacao.boleto_url:
                texto += f"\n{transacao.boleto_url}"
            await wsvc.disparar(db, cliente, texto, gatilho="boleto", processo_id=body.processo_id)
    return transacao


@router.post("/conciliacao/importar")
async def importar_extrato(
    arquivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    conteudo = (await arquivo.read()).decode("latin-1", errors="ignore")
    resultado = await conciliacao.importar_extrato(db, conteudo)
    return resultado


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(acesso_financeiro)
):
    return await svc.dashboard(db)


@router.get("/dre")
async def dre(
    inicio: date,
    fim: date,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    return await svc.dre(db, inicio, fim)


@router.get("/graficos")
async def graficos(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(acesso_financeiro)
):
    return await svc.graficos(db)


# ---------- Cobranças programadas ----------
@router.get("/cobrancas", response_model=list[CobrancaOut])
async def listar_cobrancas(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(acesso_financeiro)
):
    linhas = (
        await db.execute(
            select(CobrancaProgramada, Cliente.nome)
            .outerjoin(Cliente, CobrancaProgramada.cliente_id == Cliente.id)
            .order_by(CobrancaProgramada.ativo.desc(), CobrancaProgramada.proxima_data)
        )
    ).all()
    out = []
    for cob, nome in linhas:
        item = CobrancaOut.model_validate(cob)
        item.cliente_nome = nome
        out.append(item)
    return out


@router.post("/cobrancas", response_model=CobrancaOut, status_code=status.HTTP_201_CREATED)
async def criar_cobranca(
    body: CobrancaCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    hoje = date.today()
    proxima = body.proxima_data or date(
        hoje.year, hoje.month, min(body.dia_vencimento, 28)
    )
    if proxima < hoje and body.recorrencia == "mensal":
        proxima = svc._proximo_mes(proxima, body.dia_vencimento)
    cob = CobrancaProgramada(
        cliente_id=body.cliente_id, processo_id=body.processo_id, descricao=body.descricao,
        valor=body.valor, recorrencia=body.recorrencia, dia_vencimento=body.dia_vencimento,
        proxima_data=proxima, enviar_whatsapp=body.enviar_whatsapp, ativo=body.ativo,
    )
    db.add(cob)
    await db.flush()
    await db.refresh(cob)
    return cob


@router.put("/cobrancas/{cobranca_id}", response_model=CobrancaOut)
async def atualizar_cobranca(
    cobranca_id: int,
    body: CobrancaUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    cob = await db.get(CobrancaProgramada, cobranca_id)
    if not cob:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cobrança não encontrada")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(cob, campo, valor)
    await db.flush()
    await db.refresh(cob)
    return cob


@router.delete("/cobrancas/{cobranca_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_cobranca(
    cobranca_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(acesso_financeiro),
):
    cob = await db.get(CobrancaProgramada, cobranca_id)
    if cob:
        await db.delete(cob)


@router.post("/cobrancas/processar")
async def processar_cobrancas_agora(
    db: AsyncSession = Depends(get_db), _: Usuario = Depends(acesso_financeiro)
):
    """Processa manualmente as cobranças vencidas (gera boletos agora)."""
    return await svc.processar_cobrancas(db)


@router.get("/dashboard/stream")
async def dashboard_stream(request: Request, token: str = "", sensitive: str = ""):
    """SSE com os KPIs em tempo real. Autentica por query (EventSource não envia headers)."""
    try:
        acesso = decodificar_token(token, "access")
        sens = decodificar_token(sensitive, "sensitive")
        if int(acesso["sub"]) != int(sens["sub"]):
            raise ValueError("tokens de usuários diferentes")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tokens inválidos")

    async def gerar():
        while True:
            if await request.is_disconnected():
                break
            async with async_session_factory() as db:
                dados = await svc.dashboard(db)
            yield f"data: {json.dumps(dados)}\n\n"
            await asyncio.sleep(10)

    return StreamingResponse(gerar(), media_type="text/event-stream")
