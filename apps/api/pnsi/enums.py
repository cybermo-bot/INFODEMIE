"""Stable enum values shared by models, API schemas and the generated client.

Values are stored as text with a CHECK constraint. Never rename a value: add a
new one and migrate.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Roles from blueprint §8 (decision D14)."""

    ANALYSTE = "analyste"
    REFERENT_SCIENTIFIQUE = "referent_scientifique"
    REDACTEUR = "redacteur"
    REVISEUR_LINGUISTIQUE = "reviseur_linguistique"
    APPROBATEUR = "approbateur"
    CABINET = "cabinet"
    PARTENAIRE = "partenaire"
    RELAIS_TERRAIN = "relais_terrain"
    ADMINISTRATEUR = "administrateur"


class Locale(StrEnum):
    """Interface locales. Italian is prepared but disabled (spec §12)."""

    FR = "fr"
    AR = "ar"
    EN = "en"


class ContentLanguage(StrEnum):
    """Content language codes per span (derja-handling skill)."""

    AEB = "aeb"  # Tunisian Arabic (Derja)
    AR = "ar"  # Modern Standard Arabic
    FR = "fr"
    EN = "en"
    IT = "it"
    UND = "und"


class Script(StrEnum):
    ARABIC = "arabic"
    LATIN = "latin"


class CollectionRoute(StrEnum):
    """How an item was collected (CLAUDE.md rule 6)."""

    OFFICIAL = "official"
    ASSISTED = "assisted"
    PUBLIC_CONTESTED = "public_contested"
    INTERNAL = "internal"


class TriageRoute(StrEnum):
    """The five outputs of triage."""

    SIGNAL_SANITAIRE = "signal_sanitaire"
    ALLEGATION_RISQUE = "allegation_risque"
    QUESTION = "question"
    CRITIQUE_SERVICE = "critique_service"
    HORS_SUJET = "hors_sujet"


class SourceKind(StrEnum):
    RSS = "rss"
    SITEMAP = "sitemap"
    API = "api"
    TELEGRAM = "telegram"
    CAPTURE = "capture"
    IMPORT = "import"
    MANUAL = "manual"
    SCRAPER = "scraper"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class RunTrigger(StrEnum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class AuthorKind(StrEnum):
    ORGANISATION = "organisation"
    INDIVIDUAL = "individual"
    UNKNOWN = "unknown"


class DeletionStatus(StrEnum):
    ACTIVE = "active"
    DELETED_AT_SOURCE = "deleted_at_source"
    REMOVED = "removed"


class Stance(StrEnum):
    ASSERT = "assert"
    QUESTION = "question"
    REPORT = "report"
    SARCASM = "sarcasm"
    UNKNOWN = "unknown"


class CaseStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    ASSESSED = "assessed"
    RESPONDING = "responding"
    ACTION_RECORDED = "action_recorded"
    FOLLOW_UP = "follow_up"
    CLOSED = "closed"


class NarrativeStatus(StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    MERGED = "merged"
    SPLIT = "split"
    ARCHIVED = "archived"


class ApprovalState(StrEnum):
    """Approval of an evidence source or document version."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Verdict(StrEnum):
    CONTREDIT = "contredit"
    TROMPEUR = "trompeur"
    CONFIRME = "confirme"
    CONTESTE = "conteste"
    PREUVES_INSUFFISANTES = "preuves_insuffisantes"
    PAS_UNE_ALLEGATION = "pas_une_allegation"


class ReviewStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceRelation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXT = "context"


class ResponseKind(StrEnum):
    CORRECTION = "correction"
    CLARIFICATION = "clarification"
    FAQ = "faq"
    INVESTIGATION_NOTICE = "investigation_notice"


class VariantState(StrEnum):
    """Response variant workflow (spec §20)."""

    DRAFT = "draft"
    SCIENTIFIC_REVIEW = "scientific_review"
    LANGUAGE_REVIEW = "language_review"
    INSTITUTIONAL_REVIEW = "institutional_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    ACTION_RECORDED = "action_recorded"
    FOLLOW_UP = "follow_up"
    CLOSED = "closed"


class ApprovalKind(StrEnum):
    SCIENTIFIC = "scientific"
    LANGUAGE = "language"
    INSTITUTIONAL = "institutional"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class FollowUpWindow(StrEnum):
    H48 = "48h"
    D7 = "7d"
    D30 = "30d"


class FollowUpStatus(StrEnum):
    SCHEDULED = "scheduled"
    DONE = "done"
    MISSED = "missed"
    CANCELLED = "cancelled"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    CLOSED = "closed"


class ReportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
