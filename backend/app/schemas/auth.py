from pydantic import BaseModel, EmailStr

from app.schemas.usuario import UsuarioOut


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UsuarioOut


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SensitiveRequest(BaseModel):
    senha_sensivel: str


class SensitiveResponse(BaseModel):
    sensitive_token: str
