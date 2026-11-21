from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Prazo(Base):
    __tablename__ = "prazos"

    id: Mapped[int] = mapped_column(primary_key=True)
    processo_id: Mapped[int] = mapped_column(ForeignKey("processos.id"), index=True)
    responsavel_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data_limite: Mapped[date] = mapped_column(Date, nullable=False)
    data_limite_util: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    data_conclusao: Mapped[date | None] = mapped_column(Date)  # quando foi cumprido/perdido
    alerta_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    processo: Mapped["Processo"] = relationship(back_populates="prazos")  # noqa: F821
