"""Instância Celery. Tasks (briefing, sync, boletos) serão adicionadas nas Fases 2-4."""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "claudio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
)


@celery_app.task(name="claudio.ping")
def ping() -> str:
    return "pong"
