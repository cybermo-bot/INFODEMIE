"""Evidence registry, documents, versions, passages, assessments and evidence links.

Evidence is shared across institutions: it is public, authoritative material
(decision D7). A passage can support a verdict only if its document version and
its evidence source are approved (CLAUDE.md rule 2, spec §35 invariant 3).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Computed,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from pnsi.enums import ApprovalState, EvidenceRelation, ReviewStatus, Verdict
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

EMBEDDING_DIM = 1024  # BGE-M3 dense vectors


class EvidenceSource(UUIDPk, Mutable, Base):
    """An issuer of evidence, e.g. WHO or the Tunisian Ministry of Health."""

    __tablename__ = "evidence_sources"

    key: Mapped[str] = mapped_column(String(100), unique=True)
    issuer: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(64))
    base_url: Mapped[str | None] = mapped_column(Text)
    approval_state: Mapped[ApprovalState] = mapped_column(
        str_enum(ApprovalState),
        default=ApprovalState.PENDING,
        server_default=ApprovalState.PENDING.value,
    )
    approved_by_id: Mapped[uuid.UUID | None] = user_fk()
    approved_at: Mapped[datetime | None]
    notes: Mapped[str | None] = mapped_column(Text)


class Document(UUIDPk, Mutable, Base):
    __tablename__ = "documents"

    evidence_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT"), index=True
    )
    # Identifier of the entry in corpus/registry.yaml.
    registry_id: Mapped[str] = mapped_column(String(150), unique=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8))
    topics: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")


class DocumentVersion(UUIDPk, Mutable, Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "checksum"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), index=True
    )
    version_label: Mapped[str | None] = mapped_column(String(100))
    checksum: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(100))
    storage_path: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None]
    fetched_at: Mapped[datetime]
    approval_state: Mapped[ApprovalState] = mapped_column(
        str_enum(ApprovalState),
        default=ApprovalState.PENDING,
        server_default=ApprovalState.PENDING.value,
    )
    approved_by_id: Mapped[uuid.UUID | None] = user_fk()
    approved_at: Mapped[datetime | None]
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_versions.id", ondelete="RESTRICT")
    )
    withdrawn_at: Mapped[datetime | None]


class Passage(UUIDPk, CreatedAt, Base):
    """A citable chunk of a document version. Immutable: re-extraction makes a new version."""

    __tablename__ = "passages"
    __table_args__ = (
        UniqueConstraint("document_version_id", "ordinal"),
        Index("ix_passages_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_passages_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="RESTRICT"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # Arabic search form (derja-handling skill); display uses `text` only.
    text_ar_norm: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(8))
    page_start: Mapped[int | None]
    page_end: Mapped[int | None]
    section: Mapped[str | None] = mapped_column(Text)
    char_start: Mapped[int]
    char_end: Mapped[int]
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', coalesce(text, ''))", persisted=True),
    )


class Assessment(UUIDPk, Mutable, Scenario, Base):
    """A proposed or reviewed verdict on a claim.

    Once reviewed it is not edited: a revision is a new row with `supersedes_id`,
    so approvals can bind an exact assessment (spec §35 invariant 1).
    """

    __tablename__ = "assessments"

    institution_id: Mapped[uuid.UUID] = institution_fk()
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="RESTRICT"), index=True
    )
    proposed_verdict: Mapped[Verdict] = mapped_column(str_enum(Verdict))
    review_status: Mapped[ReviewStatus] = mapped_column(
        str_enum(ReviewStatus),
        default=ReviewStatus.PROPOSED,
        server_default=ReviewStatus.PROPOSED.value,
    )
    final_verdict: Mapped[Verdict | None] = mapped_column(str_enum(Verdict, "final_verdict"))
    rationale: Mapped[str] = mapped_column(Text)
    limitations: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    missing_evidence: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    # Models, prompt versions and the two judges' outcomes (docs/verification-engine.md).
    model_run: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    reviewer_id: Mapped[uuid.UUID | None] = user_fk()
    reviewed_at: Mapped[datetime | None]
    review_justification: Mapped[str | None] = mapped_column(Text)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="RESTRICT")
    )


class EvidenceLink(UUIDPk, CreatedAt, Base):
    """A passage cited by an assessment (spec §35). Immutable."""

    __tablename__ = "evidence_links"
    __table_args__ = (UniqueConstraint("assessment_id", "passage_id"),)

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    passage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("passages.id", ondelete="RESTRICT"), index=True
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="RESTRICT")
    )
    evidence_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT")
    )
    relation: Mapped[EvidenceRelation] = mapped_column(str_enum(EvidenceRelation))
    relevance_reason: Mapped[str] = mapped_column(Text)
    applicability: Mapped[str | None] = mapped_column(Text)
