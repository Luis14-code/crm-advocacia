from pydantic import BaseModel


class IntegracoesStatus(BaseModel):
    datajud_configurada: bool
    datajud_fonte: str  # db | env | publico
    jusbrasil_configurado: bool
    waakg_configurado: bool
    waakg_base_url: str | None = None
    waakg_session_id: str | None = None
    whatsapp_auto_envio: bool
    pagamentos_provedor: str
    pagamentos_configurado: bool


class IntegracoesUpdate(BaseModel):
    # None = não altera; "" = limpa (volta ao padrão); valor = define
    datajud_api_key: str | None = None
    jusbrasil_default_token: str | None = None
    waakg_base_url: str | None = None
    waakg_api_key: str | None = None
    waakg_session_id: str | None = None
    whatsapp_auto_envio: bool | None = None
    pagamentos_provedor: str | None = None
    pagamentos_api_key: str | None = None
    pagamentos_base_url: str | None = None


class TestarDataJud(BaseModel):
    api_key: str | None = None  # se informado, testa esta chave; senão a resolvida


class TesteResultado(BaseModel):
    ok: bool
    detalhe: str
