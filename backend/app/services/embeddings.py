"""Embeddings para RAG (memória de longo prazo).

Implementação local e determinística (bag-of-words com hashing em 384 dimensões +
normalização L2). Não exige modelos externos nem GPU — funciona de cara. É um débito
técnico consciente (Seção 17.2): pode ser trocado por um modelo semântico depois,
mantendo a mesma interface e dimensão (384).
"""
import hashlib
import math
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agente import EMBEDDING_DIM, Embedding

_TOKEN_RE = re.compile(r"[a-zá-ú0-9]+", re.IGNORECASE)
# Stopwords muito comuns em pt-BR (reduz ruído no vetor)
_STOP = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "em", "um", "uma", "para", "com",
    "que", "no", "na", "os", "as", "se", "por", "ao", "à", "é", "ou", "the",
}


def _tokens(texto: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(texto or "") if t.lower() not in _STOP and len(t) > 2]


def _hash_estavel(tok: str) -> int:
    """Hash determinístico (independe de PYTHONHASHSEED)."""
    return int.from_bytes(hashlib.md5(tok.encode()).digest()[:8], "big")


def gerar_embedding(texto: str) -> list[float]:
    """Vetor de dimensão EMBEDDING_DIM (384), normalizado (L2)."""
    vec = [0.0] * EMBEDDING_DIM
    for tok in _tokens(texto):
        h = _hash_estavel(tok)
        idx = h % EMBEDDING_DIM
        sinal = 1.0 if (h >> 63) & 1 == 0 else -1.0
        vec[idx] += sinal
    norma = math.sqrt(sum(v * v for v in vec))
    if norma > 0:
        vec = [v / norma for v in vec]
    return vec


async def indexar(
    db: AsyncSession, fonte_tipo: str, fonte_id: int, conteudo: str, metadata: dict | None = None
) -> None:
    """Gera e persiste o embedding de um conteúdo."""
    emb = gerar_embedding(conteudo)
    db.add(
        Embedding(
            fonte_tipo=fonte_tipo,
            fonte_id=fonte_id,
            conteudo=conteudo[:8000],
            embedding=emb,
            meta=metadata or {},
        )
    )


async def buscar_similar(
    db: AsyncSession,
    consulta: str,
    top_k: int = 5,
    fonte_tipo: str | None = None,
    limiar: float = 0.1,
) -> list[dict]:
    """Retorna conteúdos mais similares à consulta (distância de cosseno pgvector)."""
    qvec = gerar_embedding(consulta)
    distancia = Embedding.embedding.cosine_distance(qvec).label("dist")
    stmt = select(Embedding, distancia)
    if fonte_tipo:
        stmt = stmt.where(Embedding.fonte_tipo == fonte_tipo)
    stmt = stmt.order_by(distancia).limit(top_k)

    linhas = (await db.execute(stmt)).all()
    resultados = []
    for emb, dist in linhas:
        similaridade = 1.0 - float(dist)
        if similaridade < limiar:
            continue
        resultados.append(
            {
                "conteudo": emb.conteudo,
                "fonte_tipo": emb.fonte_tipo,
                "fonte_id": emb.fonte_id,
                "similaridade": round(similaridade, 3),
                "metadata": emb.meta,
            }
        )
    return resultados
