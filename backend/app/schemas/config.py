from pydantic import BaseModel


class IntegracoesStatus(BaseModel):
    datajud_configurada: bool
    datajud_fonte: str  # db | env | publico
    jusbrasil_configurado: bool


class IntegracoesUpdate(BaseModel):
    # None = não altera; "" = limpa (volta ao padrão); valor = define
    datajud_api_key: str | None = None
    jusbrasil_default_token: str | None = None


class TestarDataJud(BaseModel):
    api_key: str | None = None  # se informado, testa esta chave; senão a resolvida


class TesteResultado(BaseModel):
    ok: bool
    detalhe: str
