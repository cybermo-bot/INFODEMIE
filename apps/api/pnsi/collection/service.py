"""Run a connector for one source, redact, store idempotently and record the run.

Rules enforced here for every connector (source-connector skill):
- every text is redacted before it is stored (CLAUDE.md rule 4);
- every item records its route, source and run (rule 6);
- a missing key or a failure marks the run "failed" with a readable reason and
  stores nothing in its place (rule 9);
- a second identical run adds no item; a changed text becomes a revision.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pnsi.collection.registry import connector_for
from pnsi.connectors.base import Batch, Connector, ConnectorError, ItemIn, NotConfigured
from pnsi.enums import RunStatus, RunTrigger
from pnsi.log import get_logger
from pnsi.models import CollectionRun, ContentItem, ContentItemRevision, Source
from pnsi.privacy.redact import REDACTION_VERSION, redact
from pnsi.settings import Settings, get_settings

log = get_logger(__name__)

# A run stuck in queued or running longer than this no longer blocks a new one.
STALE_RUN_AFTER = timedelta(hours=1)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now() -> datetime:
    return datetime.now(UTC)


def active_run(db: Session, source: Source) -> CollectionRun | None:
    return db.scalar(
        select(CollectionRun)
        .where(
            CollectionRun.source_id == source.id,
            CollectionRun.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]),
            CollectionRun.created_at > now() - STALE_RUN_AFTER,
        )
        .limit(1)
    )


def create_run(db: Session, source: Source, trigger: RunTrigger) -> CollectionRun:
    run = CollectionRun(
        institution_id=source.institution_id,
        source_id=source.id,
        status=RunStatus.QUEUED,
        trigger=trigger,
    )
    db.add(run)
    db.flush()
    return run


def last_cursor(db: Session, source: Source) -> dict[str, Any] | None:
    return db.scalar(
        select(CollectionRun.cursor_after)
        .where(
            CollectionRun.source_id == source.id,
            CollectionRun.status.in_([RunStatus.SUCCEEDED, RunStatus.PARTIAL]),
            CollectionRun.cursor_after.is_not(None),
        )
        .order_by(CollectionRun.finished_at.desc())
        .limit(1)
    )


def _store(
    db: Session,
    source: Source,
    run: CollectionRun,
    item: ItemIn,
    parent_id: uuid.UUID | None,
    collected_at: datetime,
) -> tuple[str, ContentItem]:
    redacted = redact(item.raw_text, item.known_names)
    text = redacted.text
    content_hash = sha256(text)
    ext_hash = sha256(item.external_id)
    existing = db.scalar(
        select(ContentItem).where(
            ContentItem.source_id == source.id, ContentItem.external_id_hash == ext_hash
        )
    )
    if existing is not None:
        existing.metrics = {**existing.metrics, **item.metrics}
        if existing.content_hash == content_hash:
            return "duplicate", existing
        revision = (
            db.scalar(
                select(func.max(ContentItemRevision.revision)).where(
                    ContentItemRevision.content_item_id == existing.id
                )
            )
            or 0
        )
        db.add(
            ContentItemRevision(
                content_item_id=existing.id,
                revision=revision + 1,
                run_id=existing.run_id,
                original_text=existing.original_text,
                content_hash=existing.content_hash,
                metrics=existing.metrics,
                collected_at=existing.collected_at,
            )
        )
        existing.original_text = text
        existing.content_hash = content_hash
        existing.redaction_version = REDACTION_VERSION
        existing.run_id = run.id
        existing.collected_at = collected_at
        return "revised", existing

    row = ContentItem(
        institution_id=source.institution_id,
        source_id=source.id,
        run_id=run.id,
        route=source.route,
        external_id_hash=ext_hash,
        parent_id=parent_id,
        canonical_url=item.canonical_url,
        author_kind=item.author_kind,
        author_org_name=item.author_org_name,
        published_at=item.published_at,
        collected_at=collected_at,
        original_text=text,
        content_hash=content_hash,
        redaction_version=REDACTION_VERSION,
        metrics=item.metrics,
        is_scenario=False,
    )
    db.add(row)
    db.flush()
    return "new", row


def store_batch(db: Session, source: Source, run: CollectionRun, batch: Batch) -> None:
    collected_at = now()
    ids: dict[str, uuid.UUID] = {}
    counts = {"new": 0, "duplicate": 0, "revised": 0, "failed": 0}
    # Parents first, so comments can point at their post.
    ordered = sorted(batch.items, key=lambda i: i.parent_external_id is not None)
    for item in ordered:
        parent_id = None
        if item.parent_external_id is not None:
            parent_id = ids.get(item.parent_external_id)
            if parent_id is None:
                counts["failed"] += 1
                continue
        with db.begin_nested():
            outcome, row = _store(db, source, run, item, parent_id, collected_at)
        ids[item.external_id] = row.id
        counts[outcome] += 1
    run.items_fetched = len(batch.items)
    run.items_new = counts["new"]
    run.items_duplicate = counts["duplicate"] + counts["revised"]
    run.items_failed = counts["failed"]
    run.coverage = {**batch.coverage, "revised": counts["revised"]}


def execute_run(
    db: Session,
    run_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    connector_factory: Callable[[Source, Settings], Connector] = connector_for,
) -> CollectionRun:
    settings = settings or get_settings()
    run = db.get(CollectionRun, run_id)
    if run is None:
        raise LookupError(f"collection run {run_id} not found")
    source = db.get(Source, run.source_id)
    assert source is not None

    run.status = RunStatus.RUNNING
    run.started_at = now()
    source.last_run_at = run.started_at
    run.cursor_before = last_cursor(db, source)
    db.commit()

    try:
        connector = connector_factory(source, settings)
        batch = connector.fetch(source, run.cursor_before)
    except (NotConfigured, ConnectorError) as exc:
        _fail(db, run, source, str(exc))
        return run
    except Exception as exc:
        # Unexpected: keep the reason short and free of payload data.
        log.exception("collection_run_crashed", source_key=source.key)
        _fail(db, run, source, f"Erreur interne du connecteur ({type(exc).__name__}).")
        return run

    store_batch(db, source, run, batch)
    run.cursor_after = batch.cursor_after or run.cursor_before
    run.finished_at = now()
    if batch.partial_errors:
        run.status = RunStatus.PARTIAL
        run.error = " | ".join(batch.partial_errors)[:2000]
        source.last_error = run.error
        source.last_error_at = run.finished_at
    else:
        run.status = RunStatus.SUCCEEDED
        source.last_error = None
    source.last_success_at = run.finished_at
    db.commit()
    log.info(
        "collection_run_finished",
        source_key=source.key,
        status=run.status.value,
        new=run.items_new,
        duplicate=run.items_duplicate,
    )
    return run


def _fail(db: Session, run: CollectionRun, source: Source, reason: str) -> None:
    run.status = RunStatus.FAILED
    run.error = reason[:2000]
    run.finished_at = now()
    source.last_error = run.error
    source.last_error_at = run.finished_at
    db.commit()
    log.warning("collection_run_failed", source_key=source.key, reason=run.error)
