from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MensagemWhatsapp(Base):
    __tablename__ = "mensagens_whatsapp"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"), index=True)
    processo_id: Mapped[int | None] = mapped_column(ForeignKey("processos.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))  # quem disparou
    direcao: Mapped[str] = mapped_column(String(10), nullable=False)  # entrada | saida
    telefone: Mapped[str | None] = mapped_column(String(30))
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    gatilho: Mapped[str | None] = mapped_column(String(40))  # manual, movimentacao, boleto, aniversario...
    # saida: rascunho -> aguardando_confirmacao -> aprovada -> enviada | erro | rejeitada
    # entrada: recebida
    status: Mapped[str] = mapped_column(String(25), default="aguardando_confirmacao", index=True)
    message_id: Mapped[str | None] = mapped_column(String(120))  # id retornado pelo WA-AKG
    erro: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enviada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
