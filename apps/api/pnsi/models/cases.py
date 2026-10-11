"""Claims, mentions, cases and narratives (spec §14, §18)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Column,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from pnsi.enums import CaseStatus, NarrativeStatus, Stance
from pnsi.models.base import (
    Base,
    Mutable,
    Scenario,
    UUIDPk,
    institution_fk,
    str_enum,
    user_fk,
)


class Case(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "cases"
    __table_args__ = (UniqueConstraint("institution_id", "reference"),)

    institution_id: Mapped[uuid.UUID] = institution_fk()
    # Human reference such as D-0142, unique per institution.
    reference: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[CaseStatus] = mapped_column(
        str_enum(CaseStatus), default=CaseStatus.OPEN, server_default=CaseStatus.OPEN.value
    )
    owner_id: Mapped[uuid.UUID | None] = user_fk(index=True)
    reviewer_id: Mapped[uuid.UUID | None] = user_fk()
    editor_id: Mapped[uuid.UUID | None] = user_fk()
    escalation_contact_id: Mapped[uuid.UUID | None] = user_fk()
    due_at: Mapped[datetime | None]
    # Priority (spec §35): null value when components are missing, never a guess.
    priority_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    priority_components: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    priority_missingness: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    priority_completeness: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    priority_policy_version: Mapped[str | None] = mapped_column(String(32))
    priority_rationale: Mapped[str | None] = mapped_column(Text)


class Narrative(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "narratives"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    label: Mapped[str] = mapped_column(Text)
    theme: Mapped[str | None] = mapped_column(String(100), index=True)
    cluster_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[NarrativeStatus] = mapped_column(
        str_enum(NarrativeStatus),
        default=NarrativeStatus.PROPOSED,
        server_default=NarrativeStatus.PROPOSED.value,
    )
    confirmed_by_id: Mapped[uuid.UUID | None] = user_fk()
    confirmed_at: Mapped[datetime | None]
    # Merge and split history.
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narratives.id", ondelete="RESTRICT")
    )
    split_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narratives.id", ondelete="RESTRICT")
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")


case_narratives = Table(
    "case_narratives",
    Base.metadata,
    Column("case_id", ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("narrative_id", ForeignKey("narratives.id", ondelete="CASCADE"), primary_key=True),
)


class Claim(UUIDPk, Mutable, Scenario, Base):
    __tablename__ = "claims"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    original_text: Mapped[str] = mapped_column(Text)
    # Neutral wording that does not amplify the claim.
    neutral_text: Mapped[str | None] = mapped_column(Text)
    language_spans: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    topic_ids: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    claim_type: Mapped[str | None] = mapped_column(String(64))
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), index=True
    )
    narrative_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narratives.id", ondelete="RESTRICT"), index=True
    )
    extraction: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")


class Mention(UUIDPk, Mutable, Base):
    """A content item that carries a claim. Deduplication keeps every mention."""

    __tablename__ = "mentions"
    __table_args__ = (UniqueConstraint("claim_id", "content_item_id"),)

    institution_id: Mapped[uuid.UUID] = institution_fk()
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="RESTRICT"), index=True
    )
    stance: Mapped[Stance] = mapped_column(
        str_enum(Stance), default=Stance.UNKNOWN, server_default=Stance.UNKNOWN.value
    )
    span_start: Mapped[int | None]
    span_end: Mapped[int | None]
    attached_by_id: Mapped[uuid.UUID | None] = user_fk()
    attach_reason: Mapped[str | None] = mapped_column(Text)
