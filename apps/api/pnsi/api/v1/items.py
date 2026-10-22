"""Collected items (Signaux inbox)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from pnsi.api.v1.collection_schemas import ItemDetail, ItemOut, ItemPage
from pnsi.auth.deps import require
from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission
from pnsi.db import DbSession
from pnsi.enums import CollectionRoute
from pnsi.errors import ERROR_RESPONSES
from pnsi.services import items as item_service

router = APIRouter(prefix="/items", tags=["items"], responses=ERROR_RESPONSES)
SignalReader = Annotated[Principal, Depends(require(Permission.SIGNALS_READ))]


@router.get("", response_model=ItemPage, operation_id="list_items")
def list_items(
    principal: SignalReader,
    db: DbSession,
    source_id: uuid.UUID | None = None,
    route: CollectionRoute | None = None,
    ads: Annotated[
        bool | None,
        Query(description="false: sans les annonces commerciales ; true : annonces seulement"),
    ] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ItemPage:
    items, counts, sources = item_service.list_items(
        db, principal, source_id=source_id, route=route, ads=ads, offset=offset, limit=limit + 1
    )
    page = [ItemOut.build(i, sources[i.source_id], counts.get(i.id, 0)) for i in items[:limit]]
    return ItemPage(items=page, next_offset=offset + limit if len(items) > limit else None)


@router.get("/{item_id}", response_model=ItemDetail, operation_id="get_item")
def get_item(item_id: uuid.UUID, principal: SignalReader, db: DbSession) -> ItemDetail:
    item, replies, source = item_service.get_item(db, principal, item_id)
    return ItemDetail(
        item=ItemOut.build(item, source, len(replies)),
        replies=[ItemOut.build(r, source) for r in replies],
    )
