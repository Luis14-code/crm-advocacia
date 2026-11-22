from pydantic import BaseModel

from app.schemas.usuario import UsuarioOut


class LoginRequest(BaseModel):
    # 'str' e não EmailStr: o login apenas busca o e-mail cadastrado (EmailStr
    # rejeitaria domínios especiais como .local/.test usados em dev/seed).
    email: str
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
