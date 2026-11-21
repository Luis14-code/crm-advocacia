from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PrazoCreate(BaseModel):
    processo_id: int
    responsavel_id: int | None = None
    descricao: str
    data_limite: date
    # dias úteis a somar a partir de uma data-base (opcional, calculado no backend)
    dias_uteis: int | None = Field(default=None, ge=0)


class PrazoUpdate(BaseModel):
    status: str | None = None  # pendente | cumprido | perdido
    descricao: str | None = None
    data_limite: date | None = None


class PrazoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    processo_id: int
    responsavel_id: int | None = None
    descricao: str
    data_limite: date
    data_limite_util: date
    status: str
    created_at: datetime
