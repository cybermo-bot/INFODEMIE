"""Source registry: the Facebook watch-list, enabling sources and requesting runs."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from pnsi.audit import service as audit
from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission
from pnsi.authz.service import ensure_can, ensure_permission
from pnsi.collection import service as collection
from pnsi.connectors.facebook_apify import DEFAULTS, FacebookPagesApify, normalize_page_url
from pnsi.enums import RunTrigger, SourceKind
from pnsi.errors import ApiError, Conflict, FieldError, NotFound
from pnsi.models import CollectionRun, Source


class RunAlreadyActive(Conflict):
    code = "run_already_active"
    message = "Une collecte est déjà en cours pour cette source."


def _slug(url: str) -> str:
    tail = url.split("facebook.com/", 1)[1].lower()
    return re.sub(r"[^a-z0-9]+", "-", tail).strip("-")[:80]


def list_sources(db: Session, principal: Principal) -> Sequence[Source]:
    ensure_permission(principal, Permission.SOURCES_READ)
    return db.scalars(
        select(Source)
        .where(Source.institution_id == principal.institution_id)
        .order_by(Source.name)
    ).all()


def get_source(db: Session, principal: Principal, source_id: uuid.UUID,
               permission: Permission = Permission.SOURCES_READ) -> Source:  # fmt: skip
    ensure_permission(principal, permission)
    source = db.get(Source, source_id)
    if source is None:
        raise NotFound()
    ensure_can(principal, permission, source)
    return source


def latest_runs(db: Session, source_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CollectionRun]:
    if not source_ids:
        return {}
    rows = db.scalars(
        select(CollectionRun)
        .where(CollectionRun.source_id.in_(source_ids))
        .ext(distinct_on(CollectionRun.source_id))
        .order_by(CollectionRun.source_id, CollectionRun.created_at.desc())
    ).all()
    return {r.source_id: r for r in rows}


def add_facebook_page(
    db: Session,
    principal: Principal,
    *,
    url: str,
    name: str,
    health_filter: bool,
    checked_note: str,
    posts_per_run: int | None = None,
    comments_per_post: int | None = None,
) -> Source:
    """Add a hand-checked public Page to the watch-list (sources-plan section 2)."""
    ensure_permission(principal, Permission.SOURCES_MANAGE)
    try:
        page_url = normalize_page_url(url)
    except ValueError as exc:
        raise ApiError(
            "Adresse de Page invalide.",
            code="invalid_page_url",
            field_errors=[FieldError(field="url", message=str(exc))],
        ) from None
    key = f"facebook:{_slug(page_url)}"
    if db.scalar(select(Source.id).where(Source.key == key)):
        raise Conflict("Cette Page est déjà dans la liste de veille.", code="source_exists")

    config: dict[str, Any] = {
        "connector": FacebookPagesApify.key,
        "page_url": page_url,
        "health_filter": health_filter,
        "posts_per_run": posts_per_run or DEFAULTS["posts_per_run"],
        "comments_per_post": (
            DEFAULTS["comments_per_post"] if comments_per_post is None else comments_per_post
        ),
        "checked_by": str(principal.user_id),
        "checked_note": checked_note.strip(),
    }
    source = Source(
        institution_id=principal.institution_id,
        key=key,
        name=name.strip(),
        kind=SourceKind.SCRAPER,
        route=FacebookPagesApify.route,
        basis=FacebookPagesApify.basis,
        enabled=True,
        schedule="every:12h",
        config=config,
    )
    db.add(source)
    db.flush()
    audit.record(
        db,
        "source.created",
        actor=principal,
        object_type="source",
        object_id=source.id,
        changes={"key": {"from": None, "to": key}, "name": {"from": None, "to": source.name}},
        context={"page_url": page_url, "checked_note": config["checked_note"]},
    )
    return source


def update_source(
    db: Session,
    principal: Principal,
    source_id: uuid.UUID,
    *,
    expected_version: int,
    enabled: bool | None = None,
    health_filter: bool | None = None,
    posts_per_run: int | None = None,
    comments_per_post: int | None = None,
) -> Source:
    source = get_source(db, principal, source_id, Permission.SOURCES_MANAGE)
    if source.version != expected_version:
        raise Conflict("La source a été modifiée entre-temps. Rechargez la page.")
    before = {"enabled": source.enabled, **source.config}
    config = dict(source.config)
    for field, value in (
        ("health_filter", health_filter),
        ("posts_per_run", posts_per_run),
        ("comments_per_post", comments_per_post),
    ):
        if value is not None:
            config[field] = value
    source.config = config
    if enabled is not None:
        source.enabled = enabled
    after = {"enabled": source.enabled, **config}
    db.flush()
    audit.record(
        db,
        "source.updated",
        actor=principal,
        object_type="source",
        object_id=source.id,
        changes=audit.diff(before, after),
    )
    return source


def request_run(db: Session, principal: Principal, source_id: uuid.UUID) -> CollectionRun:
    source = get_source(db, principal, source_id, Permission.SOURCES_MANAGE)
    if collection.active_run(db, source) is not None:
        raise RunAlreadyActive()
    run = collection.create_run(db, source, RunTrigger.MANUAL)
    audit.record(
        db,
        "collection.run_requested",
        actor=principal,
        object_type="collection_run",
        object_id=run.id,
        context={"source_key": source.key},
    )
    return run


def list_runs(db: Session, principal: Principal, source_id: uuid.UUID,
              limit: int = 20) -> Sequence[CollectionRun]:  # fmt: skip
    source = get_source(db, principal, source_id)
    return db.scalars(
        select(CollectionRun)
        .where(CollectionRun.source_id == source.id)
        .order_by(CollectionRun.created_at.desc())
        .limit(limit)
    ).all()


def get_run(db: Session, principal: Principal, run_id: uuid.UUID) -> CollectionRun:
    ensure_permission(principal, Permission.SOURCES_READ)
    run = db.get(CollectionRun, run_id)
    if run is None:
        raise NotFound()
    ensure_can(principal, Permission.SOURCES_READ, run)
    return run
