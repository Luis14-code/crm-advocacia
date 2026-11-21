from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FeedbackCreate(BaseModel):
    contexto: str | None = None  # plugin ou tipo de sugestão
    sugestao: str | None = None
    util: bool | None = None
    correcao: str | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contexto: str | None = None
    util: bool | None = None
    created_at: datetime


class ResultadoCasoIn(BaseModel):
    resultado: str  # procedente | improcedente | acordo | parcial
    valor_pedido: Decimal | None = None
    valor_obtido: Decimal | None = None
    tese: str | None = None
    juiz: str | None = None
    vara: str | None = None
    estrategia_usada: str | None = None
    tempo_dias: int | None = None
    observacoes: str | None = None
