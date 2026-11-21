from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReuniaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int | None = None
    processo_id: int | None = None
    advogado_id: int | None = None
    status: str
    duracao_segundos: int | None = None
    transcricao: str | None = None
    resumo: str | None = None
    fatos_peticao: list | dict | None = None
    pendencias: list | dict | None = None
    created_at: datetime


class ReuniaoResumoOut(BaseModel):
    """Versão enxuta para listagem (sem transcrição completa)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int | None = None
    processo_id: int | None = None
    status: str
    duracao_segundos: int | None = None
    resumo: str | None = None
    created_at: datetime


class FatosUpdate(BaseModel):
    fatos_peticao: list[str] | None = None
    pendencias: list[str] | None = None
    resumo: str | None = None
