"""Collected content items and their revisions.

`original_text` is the text after redaction of personal identifiers only
(CLAUDE.md rule 4). Normalisation and translations are derived fields.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pnsi.enums import AuthorKind, CollectionRoute, DeletionStatus, TriageRoute
from pnsi.models.base import (
    Base,
    CreatedAt,
    Mutable,
    Scenario,
    UUIDPk,
    institution_fk,
    str_enum,
)


class ContentItem(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        # Re-running a collection never duplicates an item (idempotency).
        UniqueConstraint("source_id", "external_id_hash"),
        Index("ix_content_items_institution_published", "institution_id", "published_at"),
    )

    institution_id: Mapped[uuid.UUID] = institution_fk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="RESTRICT"), index=True
    )
    route: Mapped[CollectionRoute] = mapped_column(str_enum(CollectionRoute), index=True)
    # SHA-256 of the platform identifier, never the identifier itself.
    external_id_hash: Mapped[str] = mapped_column(String(64))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="RESTRICT"), index=True
    )
    # Only kept for organisation and media pages; individual profile links are redacted.
    canonical_url: Mapped[str | None] = mapped_column(Text)
    author_kind: Mapped[AuthorKind] = mapped_column(
        str_enum(AuthorKind), default=AuthorKind.UNKNOWN, server_default=AuthorKind.UNKNOWN.value
    )
    author_org_name: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None]
    collected_at: Mapped[datetime]
    original_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    redaction_version: Mapped[str] = mapped_column(String(32))
    normalized_text: Mapped[str | None] = mapped_column(Text)
    # [{start, end, lang, script}] per the derja-handling skill.
    language_spans: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    primary_language: Mapped[str | None] = mapped_column(String(8))
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    duplicate_group_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    triage_route: Mapped[TriageRoute | None] = mapped_column(str_enum(TriageRoute), index=True)
    deletion_status: Mapped[DeletionStatus] = mapped_column(
        str_enum(DeletionStatus),
        default=DeletionStatus.ACTIVE,
        server_default=DeletionStatus.ACTIVE.value,
    )
    deleted_at: Mapped[datetime | None]


class ContentItemRevision(UUIDPk, CreatedAt, Base):
    """Append-only snapshot when a collected item changes at the source."""

    __tablename__ = "content_item_revisions"
    __table_args__ = (UniqueConstraint("content_item_id", "revision"),)

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_runs.id", ondelete="RESTRICT"))
    original_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    collected_at: Mapped[datetime]
