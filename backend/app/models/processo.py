from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Processo(Base):
    __tablename__ = "processos"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(25), unique=True, nullable=False, index=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"))
    advogado_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    subtipo: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="ativo", index=True)
    resultado: Mapped[str | None] = mapped_column(String(30))
    valor_causa: Mapped[float | None] = mapped_column(Numeric(12, 2))
    valor_resultado: Mapped[float | None] = mapped_column(Numeric(12, 2))
    juiz: Mapped[str | None] = mapped_column(String(255))
    vara: Mapped[str | None] = mapped_column(String(255))
    tribunal: Mapped[str | None] = mapped_column(String(50))
    tese_principal: Mapped[str | None] = mapped_column(Text)
    data_distribuicao: Mapped[date | None] = mapped_column(Date)
    data_encerramento: Mapped[date | None] = mapped_column(Date)
    resumo_ia: Mapped[str | None] = mapped_column(Text)
    brechas_ia: Mapped[dict | None] = mapped_column(JSONB)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="processos")  # noqa: F821
    advogado: Mapped["Usuario"] = relationship(  # noqa: F821
        back_populates="processos", foreign_keys=[advogado_id]
    )
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(  # noqa: F821
        back_populates="processo", cascade="all, delete-orphan"
    )
    prazos: Mapped[list["Prazo"]] = relationship(  # noqa: F821
        back_populates="processo", cascade="all, delete-orphan"
    )
