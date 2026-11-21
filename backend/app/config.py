"""Configuração central via pydantic-settings (lida do ambiente / .env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Ambiente
    environment: str = "development"
    log_level: str = "INFO"
    domain: str = "localhost"

    # Banco
    database_url: str = "postgresql+asyncpg://claudio:claudio@db:5432/claudio"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    refresh_token_expire_days: int = 7
    sensitive_token_expire_minutes: int = 30
    sensitive_password_hash: str = ""
    fernet_key: str = ""

    # LLM
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: int = 120

    # Whisper (transcrição)
    whisper_model: str = "tiny"       # tiny para dev; medium em produção
    whisper_device: str = "cpu"       # cpu | cuda
    whisper_language: str = "pt"
    whisper_compute_type: str = "int8"  # int8 (cpu) | float16 (gpu)

    # Uploads
    upload_dir: str = "/app/uploads"
    max_upload_mb: int = 200

    # Financeiro
    iss_percentual: float = 5.0        # ISS sobre honorários
    honorarios_padrao: float = 30.0    # % contratual padrão quando não há config

    # WhatsApp (WA-AKG) — anti-ban
    whatsapp_envio_inicio: int = 8     # janela de envio (hora)
    whatsapp_envio_fim: int = 20
    whatsapp_max_por_hora: int = 20
    whatsapp_intervalo_min_seg: int = 45  # intervalo mínimo entre envios

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # WhatsApp
    waha_url: str = "http://waha:3000"
    waha_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
