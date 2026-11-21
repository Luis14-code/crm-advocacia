from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentoCreate(BaseModel):
    processo_id: int | None = None
    tipo: str
    titulo: str | None = None
    conteudo: str | None = None


class DocumentoUpdate(BaseModel):
    titulo: str | None = None
    conteudo: str | None = None


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    processo_id: int | None = None
    autor_id: int | None = None
    tipo: str
    titulo: str | None = None
    conteudo: str | None = None
    gerado_por_ia: bool
    created_at: datetime


class GerarPecaRequest(BaseModel):
    processo_id: int
    tipo: str = "peticao_inicial"
    fatos: list[str] | None = None
    reuniao_id: int | None = None  # usa os fatos extraídos dessa reunião
