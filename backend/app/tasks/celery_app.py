"""Instância Celery + agendamento (beat) do Projeto Cláudio."""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "claudio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.sync_tasks",
        "app.tasks.briefing_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
)

# Agendamento (Seção 5): sync a cada 4h; briefing matinal às 7h BRT.
celery_app.conf.beat_schedule = {
    "sync-processos-4h": {
        "task": "claudio.sync_processos",
        "schedule": crontab(minute=0, hour="*/4"),
    },
    "briefing-matinal-7h": {
        "task": "claudio.gerar_briefings",
        "schedule": crontab(minute=0, hour=7),
    },
}


@celery_app.task(name="claudio.ping")
def ping() -> str:
    return "pong"
