from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Perfil


class UsuarioBase(BaseModel):
    nome: str
    email: str  # str (não EmailStr) para aceitar domínios de dev/seed (.local)
    perfil: Perfil
    oab: str | None = None
    ativo: bool = True


class UsuarioCreate(UsuarioBase):
    senha: str = Field(min_length=6)


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    perfil: Perfil | None = None
    oab: str | None = None
    ativo: bool | None = None
    senha: str | None = Field(default=None, min_length=6)


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    preferencias: dict = {}
    created_at: datetime
