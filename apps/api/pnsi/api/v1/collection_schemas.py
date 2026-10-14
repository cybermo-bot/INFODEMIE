"""Request and response models for sources, collection runs and collected items."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pnsi.enums import AuthorKind, CollectionRoute, RunStatus, RunTrigger, SourceKind
from pnsi.models import CollectionRun, ContentItem, Source
from pnsi.settings import IntegrationState


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    status: RunStatus
    trigger: RunTrigger
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    items_fetched: int
    items_new: int
    items_duplicate: int
    items_failed: int
    error: str | None
    coverage: dict[str, Any]
    is_scenario: bool


class SourceOut(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    kind: SourceKind
    route: CollectionRoute
    basis: str
    enabled: bool
    schedule: str | None
    connector: str | None
    # State of the key the connector needs: "configure" or "non_configure".
    integration_state: IntegrationState | None
    page_url: str | None
    health_filter: bool | None
    posts_per_run: int | None
    comments_per_post: int | None
    checked_note: str | None
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error: str | None
    last_run: RunOut | None
    version: int

    @classmethod
    def build(
        cls, source: Source, last_run: CollectionRun | None, integrations: dict[str, Any]
    ) -> SourceOut:
        cfg = source.config or {}
        connector = cfg.get("connector")
        integration = "apify" if connector == "facebook_pages_apify" else None
        return cls(
            id=source.id,
            key=source.key,
            name=source.name,
            kind=source.kind,
            route=source.route,
            basis=source.basis,
            enabled=source.enabled,
            schedule=source.schedule,
            connector=connector,
            integration_state=integrations.get(integration) if integration else None,
            page_url=cfg.get("page_url"),
            health_filter=cfg.get("health_filter"),
            posts_per_run=cfg.get("posts_per_run"),
            comments_per_post=cfg.get("comments_per_post"),
            checked_note=cfg.get("checked_note"),
            last_run_at=source.last_run_at,
            last_success_at=source.last_success_at,
            last_error_at=source.last_error_at,
            last_error=source.last_error,
            last_run=RunOut.model_validate(last_run) if last_run else None,
            version=source.version,
        )


class FacebookPageCreate(BaseModel):
    url: str = Field(min_length=10, max_length=500)
    name: str = Field(min_length=2, max_length=255)
    # True for general pages (media, community); false for health institutions.
    health_filter: bool = True
    # Who checked the Page and what they saw: public, active, Tunisian, relevant.
    checked_note: str = Field(min_length=10, max_length=1000)
    posts_per_run: int | None = Field(default=None, ge=1, le=50)
    comments_per_post: int | None = Field(default=None, ge=0, le=200)


class SourcePatch(BaseModel):
    expected_version: int = Field(ge=1)
    enabled: bool | None = None
    health_filter: bool | None = None
    posts_per_run: int | None = Field(default=None, ge=1, le=50)
    comments_per_post: int | None = Field(default=None, ge=0, le=200)


class SourceRef(BaseModel):
    id: uuid.UUID
    key: str
    name: str


class ItemOut(BaseModel):
    id: uuid.UUID
    route: CollectionRoute
    source: SourceRef
    run_id: uuid.UUID
    parent_id: uuid.UUID | None
    canonical_url: str | None
    author_kind: AuthorKind
    author_org_name: str | None
    published_at: datetime | None
    collected_at: datetime
    original_text: str
    redaction_version: str
    metrics: dict[str, Any]
    is_scenario: bool
    reply_count: int

    @classmethod
    def build(cls, item: ContentItem, source: Source, reply_count: int = 0) -> ItemOut:
        return cls(
            id=item.id,
            route=item.route,
            source=SourceRef(id=source.id, key=source.key, name=source.name),
            run_id=item.run_id,
            parent_id=item.parent_id,
            canonical_url=item.canonical_url,
            author_kind=item.author_kind,
            author_org_name=item.author_org_name,
            published_at=item.published_at,
            collected_at=item.collected_at,
            original_text=item.original_text,
            redaction_version=item.redaction_version,
            metrics=item.metrics,
            is_scenario=item.is_scenario,
            reply_count=reply_count,
        )


class ItemPage(BaseModel):
    items: list[ItemOut]
    next_offset: int | None


class ItemDetail(BaseModel):
    item: ItemOut
    replies: list[ItemOut]
