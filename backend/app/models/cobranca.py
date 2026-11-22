from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CobrancaProgramada(Base):
    """Cobrança agendada/recorrente: gera boletos automaticamente e avisa no WhatsApp."""

    __tablename__ = "cobrancas_programadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    processo_id: Mapped[int | None] = mapped_column(ForeignKey("processos.id"))
    descricao: Mapped[str | None] = mapped_column(String(255))
    valor: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    recorrencia: Mapped[str] = mapped_column(String(10), default="mensal")  # mensal | unica
    dia_vencimento: Mapped[int] = mapped_column(Integer, default=10)  # dia do mês (1-28)
    proxima_data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    enviar_whatsapp: Mapped[bool] = mapped_column(Boolean, default=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultima_geracao: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
