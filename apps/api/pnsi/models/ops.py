"""Alerts, reports, the append-only audit trail and background job records."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from pnsi.enums import AlertSeverity, AlertStatus, JobStatus, ReportStatus
from pnsi.models.base import Base, Mutable, Scenario, UUIDPk, institution_fk, str_enum, user_fk


class Alert(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "alerts"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    rule_key: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(Text)
    severity: Mapped[AlertSeverity] = mapped_column(str_enum(AlertSeverity))
    status: Mapped[AlertStatus] = mapped_column(
        str_enum(AlertStatus), default=AlertStatus.OPEN, server_default=AlertStatus.OPEN.value
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    acknowledged_by_id: Mapped[uuid.UUID | None] = user_fk()
    acknowledged_at: Mapped[datetime | None]
    escalated_to_id: Mapped[uuid.UUID | None] = user_fk()


class Report(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "reports"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    kind: Mapped[str] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(8))
    period_start: Mapped[datetime | None]
    period_end: Mapped[datetime | None]
    # Filters and data snapshot the report was built from, for traceability.
    query_snapshot: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    status: Mapped[ReportStatus] = mapped_column(
        str_enum(ReportStatus),
        default=ReportStatus.QUEUED,
        server_default=ReportStatus.QUEUED.value,
    )
    file_path: Mapped[str | None] = mapped_column(Text)
    requested_by_id: Mapped[uuid.UUID] = user_fk(nullable=False)
    expires_at: Mapped[datetime | None]


class AuditEvent(Base):
    """Append-only record of every material change (spec §3, §24).

    No updated_at and no version: rows are never changed. A database trigger in
    the initial migration rejects UPDATE and DELETE. Actor and object ids are
    plain columns, not foreign keys, so the trail survives any later cleanup.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_object", "object_type", "object_id"),
        Index("ix_audit_events_institution_at", "institution_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    actor_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    actor_roles: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    institution_id: Mapped[uuid.UUID | None]
    action: Mapped[str] = mapped_column(String(100), index=True)
    object_type: Mapped[str | None] = mapped_column(String(64))
    object_id: Mapped[str | None] = mapped_column(String(64))
    # Redacted before/after values of the fields that changed.
    changes: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    context: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    request_id: Mapped[str | None] = mapped_column(String(64))


class Job(UUIDPk, Mutable, Base):
    __tablename__ = "jobs"

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus), default=JobStatus.QUEUED, server_default=JobStatus.QUEUED.value
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    result: Mapped[dict[str, Any] | None]
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    celery_task_id: Mapped[str | None] = mapped_column(String(64))
    created_by_id: Mapped[uuid.UUID | None] = user_fk()
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
