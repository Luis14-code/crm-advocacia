from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ClienteBase(BaseModel):
    nome: str
    cpf: str | None = None
    telefone: str | None = None
    email: EmailStr | None = None
    data_nascimento: date | None = None
    endereco: dict | None = None
    notas: str | None = None
    tom_comunicacao: str = "formal"
    whatsapp_opt_out: bool = False


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: str | None = None
    cpf: str | None = None
    telefone: str | None = None
    email: EmailStr | None = None
    data_nascimento: date | None = None
    endereco: dict | None = None
    notas: str | None = None
    tom_comunicacao: str | None = None
    whatsapp_opt_out: bool | None = None


class ClienteOut(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
