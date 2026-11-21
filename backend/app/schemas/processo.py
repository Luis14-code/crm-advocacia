from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProcessoBase(BaseModel):
    numero: str
    cliente_id: int | None = None
    advogado_id: int | None = None
    tipo: str
    subtipo: str | None = None
    status: str = "ativo"
    resultado: str | None = None
    valor_causa: Decimal | None = None
    valor_resultado: Decimal | None = None
    juiz: str | None = None
    vara: str | None = None
    tribunal: str | None = None
    tese_principal: str | None = None
    data_distribuicao: date | None = None
    data_encerramento: date | None = None


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoUpdate(BaseModel):
    cliente_id: int | None = None
    advogado_id: int | None = None
    tipo: str | None = None
    subtipo: str | None = None
    status: str | None = None
    resultado: str | None = None
    valor_causa: Decimal | None = None
    valor_resultado: Decimal | None = None
    juiz: str | None = None
    vara: str | None = None
    tribunal: str | None = None
    tese_principal: str | None = None
    data_distribuicao: date | None = None
    data_encerramento: date | None = None


class ProcessoOut(ProcessoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resumo_ia: str | None = None
    created_at: datetime
    updated_at: datetime
