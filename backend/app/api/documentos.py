"""Documentos/peças: CRUD, geração assistida e exportação PDF."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models.agente import Reuniao
from app.models.cliente import Cliente
from app.models.documento import Documento
from app.models.enums import Perfil
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.documento import (
    DocumentoCreate,
    DocumentoOut,
    DocumentoUpdate,
    GerarPecaRequest,
)
from app.services import embeddings, pecas

router = APIRouter(prefix="/api/documentos", tags=["documentos"])

_pode_editar = require_roles(Perfil.socio, Perfil.advogado)


@router.get("", response_model=list[DocumentoOut])
async def listar(
    processo_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = select(Documento)
    if processo_id:
        stmt = stmt.where(Documento.processo_id == processo_id)
    stmt = stmt.order_by(Documento.created_at.desc()).limit(100)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{documento_id}", response_model=DocumentoOut)
async def obter(
    documento_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    doc = await db.get(Documento, documento_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado")
    return doc


@router.post("", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def criar(
    body: DocumentoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(_pode_editar),
):
    doc = Documento(
        processo_id=body.processo_id,
        autor_id=user.id,
        tipo=body.tipo,
        titulo=body.titulo,
        conteudo=body.conteudo,
        gerado_por_ia=False,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.put("/{documento_id}", response_model=DocumentoOut)
async def atualizar(
    documento_id: int,
    body: DocumentoUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(_pode_editar),
):
    doc = await db.get(Documento, documento_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(doc, campo, valor)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.post("/gerar", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def gerar(
    body: GerarPecaRequest,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(_pode_editar),
):
    processo = await db.get(Processo, body.processo_id)
    if not processo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Processo não encontrado")
    if user.perfil == Perfil.advogado.value and processo.advogado_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este processo")

    cliente = await db.get(Cliente, processo.cliente_id) if processo.cliente_id else None

    fatos = list(body.fatos or [])
    if body.reuniao_id:
        reuniao = await db.get(Reuniao, body.reuniao_id)
        if reuniao and reuniao.fatos_peticao:
            fatos += [f for f in reuniao.fatos_peticao if isinstance(f, str)]

    conteudo = await pecas.gerar_peca(body.tipo, processo, cliente, fatos)
    doc = Documento(
        processo_id=processo.id,
        autor_id=user.id,
        tipo=body.tipo,
        titulo=f"{pecas.TIPOS.get(body.tipo, 'Peça')} — {processo.numero}",
        conteudo=conteudo,
        gerado_por_ia=True,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Indexa a peça para RAG
    await embeddings.indexar(
        db, "documento", doc.id, conteudo, metadata={"processo_id": processo.id, "tipo": body.tipo}
    )
    return doc


@router.get("/{documento_id}/pdf")
async def exportar_pdf(
    documento_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    doc = await db.get(Documento, documento_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado")
    pdf = pecas.markdown_para_pdf(doc.conteudo or "", titulo=doc.titulo or "Documento")
    nome = f"documento_{doc.id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
