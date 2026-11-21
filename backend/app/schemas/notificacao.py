from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    processo_id: int | None = None
    tipo: str
    titulo: str
    corpo: str | None = None
    lida: bool
    created_at: datetime
