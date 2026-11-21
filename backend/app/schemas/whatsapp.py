from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MensagemWhatsappOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int | None = None
    processo_id: int | None = None
    direcao: str
    telefone: str | None = None
    texto: str
    gatilho: str | None = None
    status: str
    created_at: datetime
    enviada_em: datetime | None = None


class EnviarWhatsappRequest(BaseModel):
    cliente_id: int
    processo_id: int | None = None
    texto: str | None = None
    template: str | None = None  # nome do template; usa 'texto' quando ausente
    contexto: dict | None = None  # variáveis para o template
    auto_aprovar: bool = False   # sócio pode aprovar direto


class StatusWhatsapp(BaseModel):
    configurado: bool
    conectado: bool
    detalhe: str | None = None
    telefone: str | None = None
