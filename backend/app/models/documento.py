from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    processo_id: Mapped[int | None] = mapped_column(ForeignKey("processos.id"), index=True)
    autor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    titulo: Mapped[str | None] = mapped_column(String(255))
    conteudo: Mapped[str | None] = mapped_column(Text)  # Markdown da peça
    arquivo_path: Mapped[str | None] = mapped_column(String(500))
    gerado_por_ia: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
