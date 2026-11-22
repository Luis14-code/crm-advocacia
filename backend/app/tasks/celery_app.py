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
        "app.tasks.transcricao_tasks",
        "app.tasks.whatsapp_tasks",
        "app.tasks.aprendizado_tasks",
        "app.tasks.cobrancas_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    # Transcrição vai para a fila dedicada 'whisper' (consumida pelo whisper-worker).
    task_routes={"claudio.transcrever_reuniao": {"queue": "whisper"}},
    task_default_queue="celery",
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
    "ciclo-aprendizado-2h": {
        "task": "claudio.ciclo_aprendizado",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    "cobrancas-diaria-6h": {
        "task": "claudio.processar_cobrancas",
        "schedule": crontab(minute=0, hour=6),
    },
}


@celery_app.task(name="claudio.ping")
def ping() -> str:
    return "pong"
