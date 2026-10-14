"""Collected items for the Signaux inbox. Read-only at this stage (triage comes in Stage 4)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission
from pnsi.authz.service import ensure_can, ensure_permission
from pnsi.enums import CollectionRoute, DeletionStatus
from pnsi.errors import NotFound
from pnsi.models import ContentItem, Source


def list_items(
    db: Session,
    principal: Principal,
    *,
    source_id: uuid.UUID | None = None,
    route: CollectionRoute | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[Sequence[ContentItem], dict[uuid.UUID, int], dict[uuid.UUID, Source]]:
    """Top-level items newest first, with their reply counts and sources."""
    ensure_permission(principal, Permission.SIGNALS_READ)
    query = select(ContentItem).where(
        ContentItem.institution_id == principal.institution_id,
        ContentItem.parent_id.is_(None),
        ContentItem.deletion_status == DeletionStatus.ACTIVE,
    )
    if source_id is not None:
        query = query.where(ContentItem.source_id == source_id)
    if route is not None:
        query = query.where(ContentItem.route == route)
    sort_key = func.coalesce(ContentItem.published_at, ContentItem.collected_at)
    items = db.scalars(
        query.order_by(sort_key.desc(), ContentItem.id).offset(offset).limit(limit)
    ).all()
    ids = [i.id for i in items]
    counts: dict[uuid.UUID, int] = {}
    if ids:
        counts = dict(
            db.execute(
                select(ContentItem.parent_id, func.count())
                .where(ContentItem.parent_id.in_(ids))
                .group_by(ContentItem.parent_id)
            ).all()
        )
    sources = {
        s.id: s
        for s in db.scalars(select(Source).where(Source.id.in_({i.source_id for i in items})))
    }
    return items, counts, sources


def get_item(
    db: Session, principal: Principal, item_id: uuid.UUID
) -> tuple[ContentItem, Sequence[ContentItem], Source]:
    ensure_permission(principal, Permission.SIGNALS_READ)
    item = db.get(ContentItem, item_id)
    if item is None:
        raise NotFound()
    ensure_can(principal, Permission.SIGNALS_READ, item)
    children = db.scalars(
        select(ContentItem)
        .where(ContentItem.parent_id == item.id)
        .order_by(func.coalesce(ContentItem.published_at, ContentItem.collected_at))
    ).all()
    source = db.get(Source, item.source_id)
    assert source is not None
    return item, children, source
