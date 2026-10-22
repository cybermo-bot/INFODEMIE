"""Celery application: collection runs and the schedule that starts them."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

from celery import Celery
from sqlalchemy import select

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
    beat_schedule={
        "collect-due-sources": {"task": "pnsi.collect_due", "schedule": 15 * 60},
    },
)

_EVERY = re.compile(r"^every:(\d+)([mh])$")


def schedule_interval(schedule: str | None) -> timedelta | None:
    """`every:12h` or `every:30m`; anything else means manual only."""
    m = _EVERY.match(schedule or "")
    if not m:
        return None
    value, unit = int(m.group(1)), m.group(2)
    return timedelta(hours=value) if unit == "h" else timedelta(minutes=value)


@celery_app.task(name="pnsi.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="pnsi.collect_run")
def collect_run(run_id: str) -> str:
    from pnsi.collection.service import execute_run
    from pnsi.db import get_sessionmaker

    with get_sessionmaker()() as db:
        run = execute_run(db, uuid.UUID(run_id))
        return run.status.value


@celery_app.task(name="pnsi.collect_due")
def collect_due() -> int:
    """Queue a run for every enabled source whose interval has elapsed."""
    from pnsi.collection.service import active_run, create_run, fail_stale_runs
    from pnsi.db import get_sessionmaker
    from pnsi.enums import RunTrigger
    from pnsi.models import Source

    started = 0
    now = datetime.now(UTC)
    with get_sessionmaker()() as db:
        fail_stale_runs(db)
        for source in db.scalars(select(Source).where(Source.enabled.is_(True))).all():
            interval = schedule_interval(source.schedule)
            if interval is None or not (source.config or {}).get("connector"):
                continue
            if source.last_run_at and now - source.last_run_at < interval:
                continue
            if active_run(db, source) is not None:
                continue
            run = create_run(db, source, RunTrigger.SCHEDULED)
            db.commit()
            collect_run.delay(str(run.id))
            started += 1
    return started
