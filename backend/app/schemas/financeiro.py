from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransacaoCreate(BaseModel):
    processo_id: int | None = None
    cliente_id: int | None = None
    tipo: str  # entrada | saida
    categoria: str | None = None  # honorarios | custas | despesa | boleto
    descricao: str | None = None
    valor: Decimal
    data_vencimento: date | None = None
    data_pagamento: date | None = None
    status: str = "pendente"
    parcela_num: int | None = None
    parcela_total: int | None = None


class TransacaoUpdate(BaseModel):
    categoria: str | None = None
    descricao: str | None = None
    valor: Decimal | None = None
    data_vencimento: date | None = None
    data_pagamento: date | None = None
    status: str | None = None


class TransacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    processo_id: int | None = None
    cliente_id: int | None = None
    tipo: str
    categoria: str | None = None
    descricao: str | None = None
    valor: Decimal
    data_vencimento: date | None = None
    data_pagamento: date | None = None
    status: str
    boleto_url: str | None = None
    parcela_num: int | None = None
    parcela_total: int | None = None
    created_at: datetime


class SimularAcordoRequest(BaseModel):
    processo_id: int
    valor_bruto: Decimal = Field(gt=0)
    parcelas: int = Field(default=1, ge=1, le=60)


class GerarBoletoRequest(BaseModel):
    cliente_id: int
    processo_id: int | None = None
    valor: Decimal = Field(gt=0)
    vencimento: date
    descricao: str | None = None
    enviar_whatsapp: bool = False


class CobrancaCreate(BaseModel):
    cliente_id: int
    processo_id: int | None = None
    descricao: str | None = None
    valor: Decimal = Field(gt=0)
    recorrencia: str = "mensal"  # mensal | unica
    dia_vencimento: int = Field(default=10, ge=1, le=28)
    proxima_data: date | None = None
    enviar_whatsapp: bool = True
    ativo: bool = True


class CobrancaUpdate(BaseModel):
    descricao: str | None = None
    valor: Decimal | None = None
    recorrencia: str | None = None
    dia_vencimento: int | None = Field(default=None, ge=1, le=28)
    proxima_data: date | None = None
    enviar_whatsapp: bool | None = None
    ativo: bool | None = None


class CobrancaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    cliente_nome: str | None = None
    processo_id: int | None = None
    descricao: str | None = None
    valor: Decimal
    recorrencia: str
    dia_vencimento: int
    proxima_data: date
    enviar_whatsapp: bool
    ativo: bool
    ultima_geracao: date | None = None
