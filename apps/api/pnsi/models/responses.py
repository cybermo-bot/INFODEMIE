"""Responses, variants with immutable revisions, approvals, actions and follow-ups.

Structural guarantees for spec §35:
- an approval and an action reference an exact variant revision through a
  composite foreign key (invariants 2 and 4);
- one follow-up per action and horizon (48h, 7d, 30d) (invariant 8).
The workflow rules themselves live in the domain services (Stage 5).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from pnsi.enums import (
    ApprovalDecision,
    ApprovalKind,
    FollowUpStatus,
    FollowUpWindow,
    ResponseKind,
    Role,
    Script,
    VariantState,
)
from pnsi.models.base import (
    Base,
    CreatedAt,
    Mutable,
    Scenario,
    UUIDPk,
    institution_fk,
    str_enum,
    user_fk,
)

REVISIONS = "response_variant_revisions"


class Response(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "responses"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), index=True
    )
    # The exact assessment the response is based on.
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT")
    )
    kind: Mapped[ResponseKind] = mapped_column(str_enum(ResponseKind))
    title: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID] = user_fk(nullable=False)


class ResponseVariant(UUIDPk, Mutable, Base):
    """One language, script and channel of a response. `version` is its current revision."""

    __tablename__ = "response_variants"
    __table_args__ = (UniqueConstraint("response_id", "locale", "script", "channel"),)

    institution_id: Mapped[uuid.UUID] = institution_fk()
    response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("responses.id", ondelete="CASCADE"), index=True
    )
    # Content locale: fr, ar, en or aeb (Derja).
    locale: Mapped[str] = mapped_column(String(8))
    script: Mapped[Script] = mapped_column(str_enum(Script))
    channel: Mapped[str] = mapped_column(String(64))
    body: Mapped[str] = mapped_column(Text)
    body_hash: Mapped[str] = mapped_column(String(64))
    citation_ids: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT")
    )
    state: Mapped[VariantState] = mapped_column(
        str_enum(VariantState),
        default=VariantState.DRAFT,
        server_default=VariantState.DRAFT.value,
    )
    # AI-produced text stays labelled until a person has reviewed it (spec §20).
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class ResponseVariantRevision(UUIDPk, CreatedAt, Base):
    """Immutable snapshot of each variant version. Approvals point here."""

    __tablename__ = "response_variant_revisions"
    __table_args__ = (UniqueConstraint("response_variant_id", "version"),)

    response_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("response_variants.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    body_hash: Mapped[str] = mapped_column(String(64))
    citation_ids: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT")
    )
    edited_by_id: Mapped[uuid.UUID] = user_fk(nullable=False)


class Approval(UUIDPk, Mutable, Base):
    """A decision on one exact variant version. Any edit invalidates it (spec §20)."""

    __tablename__ = "approvals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["response_variant_id", "exact_version"],
            [f"{REVISIONS}.response_variant_id", f"{REVISIONS}.version"],
            ondelete="RESTRICT",
            name="fk_approvals_variant_revision",
        ),
    )

    institution_id: Mapped[uuid.UUID] = institution_fk()
    response_variant_id: Mapped[uuid.UUID] = mapped_column(index=True)
    exact_version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[ApprovalKind] = mapped_column(str_enum(ApprovalKind))
    decision: Mapped[ApprovalDecision] = mapped_column(str_enum(ApprovalDecision))
    reason: Mapped[str | None] = mapped_column(Text)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT")
    )
    body_hash: Mapped[str] = mapped_column(String(64))
    evidence_snapshot_hash: Mapped[str] = mapped_column(String(64))
    approver_id: Mapped[uuid.UUID] = user_fk(nullable=False)
    approver_role: Mapped[Role] = mapped_column(str_enum(Role, "approver_role"))
    decided_at: Mapped[datetime]
    invalidated_at: Mapped[datetime | None]
    invalidation_reason: Mapped[str | None] = mapped_column(Text)


class Action(UUIDPk, Mutable, Scenario, Base):
    """A publication recorded by a person. Never performed by PNSI itself."""

    __tablename__ = "actions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["response_variant_id", "variant_version"],
            [f"{REVISIONS}.response_variant_id", f"{REVISIONS}.version"],
            ondelete="RESTRICT",
            name="fk_actions_variant_revision",
        ),
    )

    institution_id: Mapped[uuid.UUID] = institution_fk()
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), index=True
    )
    response_variant_id: Mapped[uuid.UUID] = mapped_column(index=True)
    variant_version: Mapped[int] = mapped_column(Integer)
    approval_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approvals.id", ondelete="RESTRICT"))
    channel: Mapped[str] = mapped_column(String(64))
    performed_at: Mapped[datetime]
    actor_id: Mapped[uuid.UUID] = user_fk(nullable=False)
    permitted_reference: Mapped[str | None] = mapped_column(Text)
    follow_up_plan: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    notes: Mapped[str | None] = mapped_column(Text)


class FollowUp(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "follow_ups"
    __table_args__ = (UniqueConstraint("action_id", "horizon"),)

    institution_id: Mapped[uuid.UUID] = institution_fk()
    action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("actions.id", ondelete="CASCADE"), index=True
    )
    horizon: Mapped[FollowUpWindow] = mapped_column(str_enum(FollowUpWindow))
    due_at: Mapped[datetime] = mapped_column(index=True)
    status: Mapped[FollowUpStatus] = mapped_column(
        str_enum(FollowUpStatus),
        default=FollowUpStatus.SCHEDULED,
        server_default=FollowUpStatus.SCHEDULED.value,
    )
    observations: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    coverage_comparable: Mapped[bool | None]
    interpretation: Mapped[str | None] = mapped_column(Text)
    completed_by_id: Mapped[uuid.UUID | None] = user_fk()
    completed_at: Mapped[datetime | None]
