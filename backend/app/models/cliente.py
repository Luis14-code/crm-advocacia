from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True, index=True)
    telefone: Mapped[str | None] = mapped_column(String(20))  # WhatsApp principal
    email: Mapped[str | None] = mapped_column(String(255))
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    endereco: Mapped[dict | None] = mapped_column(JSONB)
    notas: Mapped[str | None] = mapped_column(Text)
    tom_comunicacao: Mapped[str] = mapped_column(String(20), default="formal")
    whatsapp_opt_out: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    processos: Mapped[list["Processo"]] = relationship(back_populates="cliente")  # noqa: F821
