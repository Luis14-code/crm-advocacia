from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

EMBEDDING_DIM = 384


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    acao: Mapped[str] = mapped_column(String(100), nullable=False)
    plugin: Mapped[str | None] = mapped_column(String(50))
    parametros: Mapped[dict | None] = mapped_column(JSONB)
    resultado: Mapped[dict | None] = mapped_column(JSONB)
    sucesso: Mapped[bool | None] = mapped_column(Boolean)
    duracao_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    contexto: Mapped[str | None] = mapped_column(String(100))
    sugestao: Mapped[str | None] = mapped_column(Text)
    util: Mapped[bool | None] = mapped_column(Boolean)
    correcao: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResultadoCaso(Base):
    __tablename__ = "resultados_caso"

    id: Mapped[int] = mapped_column(primary_key=True)
    processo_id: Mapped[int] = mapped_column(ForeignKey("processos.id"), unique=True)
    tese: Mapped[str | None] = mapped_column(String(255))
    juiz: Mapped[str | None] = mapped_column(String(255))
    vara: Mapped[str | None] = mapped_column(String(255))
    resultado: Mapped[str | None] = mapped_column(String(30))
    valor_pedido: Mapped[float | None] = mapped_column(Numeric(12, 2))
    valor_obtido: Mapped[float | None] = mapped_column(Numeric(12, 2))
    tempo_dias: Mapped[int | None] = mapped_column(Integer)
    estrategia_usada: Mapped[str | None] = mapped_column(Text)
    observacoes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    fonte_tipo: Mapped[str | None] = mapped_column(String(30))
    fonte_id: Mapped[int | None] = mapped_column(Integer)
    conteudo: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Reuniao(Base):
    __tablename__ = "reunioes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"))
    processo_id: Mapped[int | None] = mapped_column(ForeignKey("processos.id"))
    advogado_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    status: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente|transcrevendo|concluido|erro
    duracao_segundos: Mapped[int | None] = mapped_column(Integer)
    audio_path: Mapped[str | None] = mapped_column(String(500))
    transcricao: Mapped[str | None] = mapped_column(Text)
    resumo: Mapped[str | None] = mapped_column(Text)
    fatos_peticao: Mapped[dict | None] = mapped_column(JSONB)
    pendencias: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Mensagem(Base):
    __tablename__ = "mensagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
