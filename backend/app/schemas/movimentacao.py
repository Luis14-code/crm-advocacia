from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MovimentacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    processo_id: int
    data: date
    descricao: str
    fonte: str
    tipo: str | None = None
    created_at: datetime
