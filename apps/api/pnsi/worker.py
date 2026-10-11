"""Celery application. Tasks are added per stage; beat schedules come with connectors (Stage 2)."""

from __future__ import annotations

from celery import Celery

from pnsi.settings import get_settings

settings = get_settings()

celery_app = Celery("pnsi", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={},
)


@celery_app.task(name="pnsi.ping")
def ping() -> str:
    return "pong"
