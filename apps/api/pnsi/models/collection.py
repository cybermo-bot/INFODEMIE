"""Source registry and collection runs (spec §7, §14)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pnsi.enums import CollectionRoute, RunStatus, RunTrigger, SourceKind
from pnsi.models.base import Base, Mutable, Scenario, UUIDPk, institution_fk, str_enum


class Source(UUIDPk, Mutable, Base):
    __tablename__ = "sources"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[SourceKind] = mapped_column(str_enum(SourceKind))
    route: Mapped[CollectionRoute] = mapped_column(str_enum(CollectionRoute))
    # Legal or permission basis for collecting from this source (spec §6).
    basis: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    schedule: Mapped[str | None] = mapped_column(String(100))
    # Non-secret configuration only. Keys stay in the environment.
    config: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    last_run_at: Mapped[datetime | None]
    last_success_at: Mapped[datetime | None]
    last_error_at: Mapped[datetime | None]
    last_error: Mapped[str | None] = mapped_column(Text)


class CollectionRun(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "collection_runs"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[RunStatus] = mapped_column(str_enum(RunStatus), index=True)
    trigger: Mapped[RunTrigger] = mapped_column(str_enum(RunTrigger))
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    cursor_before: Mapped[dict[str, Any] | None]
    cursor_after: Mapped[dict[str, Any] | None]
    items_fetched: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    items_new: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    items_duplicate: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    items_failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error: Mapped[str | None] = mapped_column(Text)
    # What was covered: queries, pages, time window, known gaps.
    coverage: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
