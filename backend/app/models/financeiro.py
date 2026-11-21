from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transacao(Base):
    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    processo_id: Mapped[int | None] = mapped_column(ForeignKey("processos.id"))
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"))
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # entrada | saida
    categoria: Mapped[str | None] = mapped_column(String(50))
    descricao: Mapped[str | None] = mapped_column(Text)
    valor: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    data_vencimento: Mapped[date | None] = mapped_column(Date, index=True)
    data_pagamento: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    boleto_id: Mapped[str | None] = mapped_column(String(100))
    boleto_url: Mapped[str | None] = mapped_column(String(500))
    parcela_num: Mapped[int | None] = mapped_column(Integer)
    parcela_total: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConfigHonorarios(Base):
    __tablename__ = "config_honorarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_processo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    percentual_contratual: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    percentual_sucumbencial: Mapped[float | None] = mapped_column(Numeric(5, 2))
    observacoes: Mapped[str | None] = mapped_column(Text)
