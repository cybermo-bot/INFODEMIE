"""Hand a queued run to the worker, after the request transaction has committed."""

from __future__ import annotations

import uuid

from pnsi.db import get_sessionmaker
from pnsi.enums import RunStatus
from pnsi.log import get_logger
from pnsi.models import CollectionRun, Source

log = get_logger(__name__)
TASK_NAME = "pnsi.collect_run"


def enqueue_run(run_id: uuid.UUID) -> None:
    from pnsi.worker import celery_app

    try:
        celery_app.send_task(TASK_NAME, args=[str(run_id)])
    except Exception as exc:
        # Rule 9: the failure is visible on the run and the source, never silent.
        log.warning("collection_enqueue_failed", run_id=str(run_id), error=type(exc).__name__)
        with get_sessionmaker()() as db:
            run = db.get(CollectionRun, run_id)
            if run is not None and run.status == RunStatus.QUEUED:
                run.status = RunStatus.FAILED
                run.error = "File d'attente injoignable (Redis) : collecte non lancée."
                source = db.get(Source, run.source_id)
                if source is not None:
                    source.last_error = run.error
                db.commit()
