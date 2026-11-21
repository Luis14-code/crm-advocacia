from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Configuracao(Base):
    """Configuração chave-valor do escritório. Valores secretos ficam cifrados (Fernet)."""

    __tablename__ = "configuracoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    valor: Mapped[str | None] = mapped_column(Text)  # cifrado quando secreto=True
    secreto: Mapped[bool] = mapped_column(Boolean, default=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
