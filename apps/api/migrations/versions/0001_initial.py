"""Initial schema: identity, collection, content, cases, evidence, responses, ops.

Revision ID: 0001
Revises:
Create Date: 2026-10-11

Generated from the SQLAlchemy metadata without a database (see
docs/status.md), then completed by hand with the extensions and the
append-only trigger on audit_events. Run `make migration-check` once
Postgres is up to confirm models and migration agree.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_GUARD_FUNCTION = """
CREATE OR REPLACE FUNCTION audit_events_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only: % is not allowed', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
"""

AUDIT_GUARD_TRIGGER = """
CREATE TRIGGER audit_events_no_update_delete
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
"""

AUDIT_GUARD_TRUNCATE = """
CREATE TRIGGER audit_events_no_truncate
BEFORE TRUNCATE ON audit_events
FOR EACH STATEMENT EXECUTE FUNCTION audit_events_append_only();
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "actor_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("institution_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=True),
        sa.Column("object_id", sa.String(length=64), nullable=True),
        sa.Column(
            "changes", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "context", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        sa.UniqueConstraint("event_id", name=op.f("uq_audit_events_event_id")),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_audit_events_actor_id"), "audit_events", ["actor_id"], unique=False)
    op.create_index(
        "ix_audit_events_institution_at",
        "audit_events",
        ["institution_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_object", "audit_events", ["object_type", "object_id"], unique=False
    )
    op.create_table(
        "institutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name_fr", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institutions")),
        sa.UniqueConstraint("code", name=op.f("uq_institutions_code")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "locale",
            sa.Enum("fr", "ar", "en", name="locale", native_enum=False, create_constraint=False),
            server_default="fr",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint("locale IN ('fr', 'ar', 'en')", name=op.f("ck_users_locale")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_review",
                "assessed",
                "responding",
                "action_recorded",
                "follow_up",
                "closed",
                name="casestatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="open",
            nullable=False,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("editor_id", sa.Uuid(), nullable=True),
        sa.Column("escalation_contact_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority_value", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "priority_components",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "priority_missingness",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("priority_completeness", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("priority_policy_version", sa.String(length=32), nullable=True),
        sa.Column("priority_rationale", sa.Text(), nullable=True),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'in_review', 'assessed', 'responding', 'action_recorded', 'follow_up', 'closed')",
            name=op.f("ck_cases_casestatus"),
        ),
        sa.ForeignKeyConstraint(
            ["editor_id"], ["users.id"], name=op.f("fk_cases_editor_id_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["escalation_contact_id"],
            ["users.id"],
            name=op.f("fk_cases_escalation_contact_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_cases_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_cases_owner_id_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name=op.f("fk_cases_reviewer_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
        sa.UniqueConstraint(
            "institution_id", "reference", name=op.f("uq_cases_institution_id_reference")
        ),
    )
    op.create_index(op.f("ix_cases_institution_id"), "cases", ["institution_id"], unique=False)
    op.create_index(op.f("ix_cases_owner_id"), "cases", ["owner_id"], unique=False)
    op.create_index(op.f("ix_cases_topic"), "cases", ["topic"], unique=False)
    op.create_table(
        "evidence_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column(
            "approval_state",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "withdrawn",
                name="approvalstate",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("approved_by_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "approval_state IN ('pending', 'approved', 'rejected', 'withdrawn')",
            name=op.f("ck_evidence_sources_approvalstate"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
            name=op.f("fk_evidence_sources_approved_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_sources")),
        sa.UniqueConstraint("key", name=op.f("uq_evidence_sources_key")),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "succeeded",
                "failed",
                name="jobstatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')", name=op.f("ck_jobs_jobstatus")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_jobs_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_jobs_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_jobs_idempotency_key")),
    )
    op.create_index(op.f("ix_jobs_institution_id"), "jobs", ["institution_id"], unique=False)
    op.create_index(op.f("ix_jobs_kind"), "jobs", ["kind"], unique=False)
    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_memberships_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_memberships_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memberships")),
        sa.UniqueConstraint(
            "user_id", "institution_id", name=op.f("uq_memberships_user_id_institution_id")
        ),
    )
    op.create_index(
        op.f("ix_memberships_institution_id"), "memberships", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)
    op.create_table(
        "narratives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("theme", sa.String(length=100), nullable=True),
        sa.Column("cluster_version", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "proposed",
                "confirmed",
                "merged",
                "split",
                "archived",
                name="narrativestatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="proposed",
            nullable=False,
        ),
        sa.Column("confirmed_by_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_into_id", sa.Uuid(), nullable=True),
        sa.Column("split_from_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metrics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('proposed', 'confirmed', 'merged', 'split', 'archived')",
            name=op.f("ck_narratives_narrativestatus"),
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_id"],
            ["users.id"],
            name=op.f("fk_narratives_confirmed_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_narratives_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_id"],
            ["narratives.id"],
            name=op.f("fk_narratives_merged_into_id_narratives"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["split_from_id"],
            ["narratives.id"],
            name=op.f("fk_narratives_split_from_id_narratives"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_narratives")),
    )
    op.create_index(
        op.f("ix_narratives_institution_id"), "narratives", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_narratives_theme"), "narratives", ["theme"], unique=False)
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "query_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "ready",
                "failed",
                "expired",
                name="reportstatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'ready', 'failed', 'expired')",
            name=op.f("ck_reports_reportstatus"),
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_reports_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
            name=op.f("fk_reports_requested_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
    )
    op.create_index(op.f("ix_reports_institution_id"), "reports", ["institution_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "rss",
                "sitemap",
                "api",
                "telegram",
                "capture",
                "import",
                "manual",
                "scraper",
                name="sourcekind",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "route",
            sa.Enum(
                "official",
                "assisted",
                "public_contested",
                "internal",
                name="collectionroute",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("schedule", sa.String(length=100), nullable=True),
        sa.Column(
            "config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "kind IN ('rss', 'sitemap', 'api', 'telegram', 'capture', 'import', 'manual', 'scraper')",
            name=op.f("ck_sources_sourcekind"),
        ),
        sa.CheckConstraint(
            "route IN ('official', 'assisted', 'public_contested', 'internal')",
            name=op.f("ck_sources_collectionroute"),
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_sources_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("key", name=op.f("uq_sources_key")),
    )
    op.create_index(op.f("ix_sources_institution_id"), "sources", ["institution_id"], unique=False)
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "info",
                "warning",
                "critical",
                name="alertseverity",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "acknowledged",
                "escalated",
                "closed",
                name="alertstatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="open",
            nullable=False,
        ),
        sa.Column("case_id", sa.Uuid(), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("acknowledged_by_id", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_to_id", sa.Uuid(), nullable=True),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical')", name=op.f("ck_alerts_alertseverity")
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'escalated', 'closed')",
            name=op.f("ck_alerts_alertstatus"),
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_id"],
            ["users.id"],
            name=op.f("fk_alerts_acknowledged_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_alerts_case_id_cases"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["escalated_to_id"],
            ["users.id"],
            name=op.f("fk_alerts_escalated_to_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_alerts_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(op.f("ix_alerts_case_id"), "alerts", ["case_id"], unique=False)
    op.create_index(op.f("ix_alerts_institution_id"), "alerts", ["institution_id"], unique=False)
    op.create_table(
        "case_narratives",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("narrative_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_case_narratives_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["narrative_id"],
            ["narratives.id"],
            name=op.f("fk_case_narratives_narrative_id_narratives"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("case_id", "narrative_id", name=op.f("pk_case_narratives")),
    )
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("neutral_text", sa.Text(), nullable=True),
        sa.Column(
            "language_spans",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "topic_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("claim_type", sa.String(length=64), nullable=True),
        sa.Column("case_id", sa.Uuid(), nullable=True),
        sa.Column("narrative_id", sa.Uuid(), nullable=True),
        sa.Column(
            "extraction",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_claims_case_id_cases"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_claims_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["narrative_id"],
            ["narratives.id"],
            name=op.f("fk_claims_narrative_id_narratives"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claims")),
    )
    op.create_index(op.f("ix_claims_case_id"), "claims", ["case_id"], unique=False)
    op.create_index(op.f("ix_claims_institution_id"), "claims", ["institution_id"], unique=False)
    op.create_index(op.f("ix_claims_narrative_id"), "claims", ["narrative_id"], unique=False)
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "succeeded",
                "partial",
                "failed",
                name="runstatus",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "trigger",
            sa.Enum(
                "scheduled", "manual", name="runtrigger", native_enum=False, create_constraint=False
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor_before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cursor_after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("items_fetched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("items_new", sa.Integer(), server_default="0", nullable=False),
        sa.Column("items_duplicate", sa.Integer(), server_default="0", nullable=False),
        sa.Column("items_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "coverage", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed')",
            name=op.f("ck_collection_runs_runstatus"),
        ),
        sa.CheckConstraint(
            "trigger IN ('scheduled', 'manual')", name=op.f("ck_collection_runs_runtrigger")
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_collection_runs_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_collection_runs_source_id_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collection_runs")),
    )
    op.create_index(
        op.f("ix_collection_runs_institution_id"),
        "collection_runs",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collection_runs_source_id"), "collection_runs", ["source_id"], unique=False
    )
    op.create_index(op.f("ix_collection_runs_status"), "collection_runs", ["status"], unique=False)
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.Column("registry_id", sa.String(length=150), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column(
            "topics", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"],
            ["evidence_sources.id"],
            name=op.f("fk_documents_evidence_source_id_evidence_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("registry_id", name=op.f("uq_documents_registry_id")),
    )
    op.create_index(
        op.f("ix_documents_evidence_source_id"), "documents", ["evidence_source_id"], unique=False
    )
    op.create_table(
        "membership_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "analyste",
                "referent_scientifique",
                "redacteur",
                "reviseur_linguistique",
                "approbateur",
                "cabinet",
                "partenaire",
                "relais_terrain",
                "administrateur",
                name="role",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("granted_by_id", sa.Uuid(), nullable=True),
        sa.Column("justification", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('analyste', 'referent_scientifique', 'redacteur', 'reviseur_linguistique', 'approbateur', 'cabinet', 'partenaire', 'relais_terrain', 'administrateur')",
            name=op.f("ck_membership_roles_role"),
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_id"],
            ["users.id"],
            name=op.f("fk_membership_roles_granted_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["memberships.id"],
            name=op.f("fk_membership_roles_membership_id_memberships"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_membership_roles")),
        sa.UniqueConstraint(
            "membership_id", "role", name=op.f("uq_membership_roles_membership_id_role")
        ),
    )
    op.create_index(
        op.f("ix_membership_roles_membership_id"),
        "membership_roles",
        ["membership_id"],
        unique=False,
    )
    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column(
            "proposed_verdict",
            sa.Enum(
                "contredit",
                "trompeur",
                "confirme",
                "conteste",
                "preuves_insuffisantes",
                "pas_une_allegation",
                name="verdict",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "review_status",
            sa.Enum(
                "proposed",
                "accepted",
                "corrected",
                "rejected",
                "superseded",
                name="reviewstatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="proposed",
            nullable=False,
        ),
        sa.Column(
            "final_verdict",
            sa.Enum(
                "contredit",
                "trompeur",
                "confirme",
                "conteste",
                "preuves_insuffisantes",
                "pas_une_allegation",
                name="final_verdict",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=True,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "limitations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "missing_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "model_run",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_justification", sa.Text(), nullable=True),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "final_verdict IN ('contredit', 'trompeur', 'confirme', 'conteste', 'preuves_insuffisantes', 'pas_une_allegation')",
            name=op.f("ck_assessments_final_verdict"),
        ),
        sa.CheckConstraint(
            "proposed_verdict IN ('contredit', 'trompeur', 'confirme', 'conteste', 'preuves_insuffisantes', 'pas_une_allegation')",
            name=op.f("ck_assessments_verdict"),
        ),
        sa.CheckConstraint(
            "review_status IN ('proposed', 'accepted', 'corrected', 'rejected', 'superseded')",
            name=op.f("ck_assessments_reviewstatus"),
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["claims.id"],
            name=op.f("fk_assessments_claim_id_claims"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_assessments_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name=op.f("fk_assessments_reviewer_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["assessments.id"],
            name=op.f("fk_assessments_supersedes_id_assessments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessments")),
    )
    op.create_index(op.f("ix_assessments_claim_id"), "assessments", ["claim_id"], unique=False)
    op.create_index(
        op.f("ix_assessments_institution_id"), "assessments", ["institution_id"], unique=False
    )
    op.create_table(
        "content_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column(
            "route",
            sa.Enum(
                "official",
                "assisted",
                "public_contested",
                "internal",
                name="collectionroute",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("external_id_hash", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column(
            "author_kind",
            sa.Enum(
                "organisation",
                "individual",
                "unknown",
                name="authorkind",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("author_org_name", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("redaction_version", sa.String(length=32), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column(
            "language_spans",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("primary_language", sa.String(length=8), nullable=True),
        sa.Column(
            "metrics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("duplicate_group_id", sa.Uuid(), nullable=True),
        sa.Column(
            "triage_route",
            sa.Enum(
                "signal_sanitaire",
                "allegation_risque",
                "question",
                "critique_service",
                "hors_sujet",
                name="triageroute",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "deletion_status",
            sa.Enum(
                "active",
                "deleted_at_source",
                "removed",
                name="deletionstatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "author_kind IN ('organisation', 'individual', 'unknown')",
            name=op.f("ck_content_items_authorkind"),
        ),
        sa.CheckConstraint(
            "deletion_status IN ('active', 'deleted_at_source', 'removed')",
            name=op.f("ck_content_items_deletionstatus"),
        ),
        sa.CheckConstraint(
            "route IN ('official', 'assisted', 'public_contested', 'internal')",
            name=op.f("ck_content_items_collectionroute"),
        ),
        sa.CheckConstraint(
            "triage_route IN ('signal_sanitaire', 'allegation_risque', 'question', 'critique_service', 'hors_sujet')",
            name=op.f("ck_content_items_triageroute"),
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_content_items_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["content_items.id"],
            name=op.f("fk_content_items_parent_id_content_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["collection_runs.id"],
            name=op.f("fk_content_items_run_id_collection_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_content_items_source_id_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_items")),
        sa.UniqueConstraint(
            "source_id",
            "external_id_hash",
            name=op.f("uq_content_items_source_id_external_id_hash"),
        ),
    )
    op.create_index(
        op.f("ix_content_items_content_hash"), "content_items", ["content_hash"], unique=False
    )
    op.create_index(
        op.f("ix_content_items_duplicate_group_id"),
        "content_items",
        ["duplicate_group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_items_institution_id"), "content_items", ["institution_id"], unique=False
    )
    op.create_index(
        "ix_content_items_institution_published",
        "content_items",
        ["institution_id", "published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_items_parent_id"), "content_items", ["parent_id"], unique=False
    )
    op.create_index(op.f("ix_content_items_route"), "content_items", ["route"], unique=False)
    op.create_index(op.f("ix_content_items_run_id"), "content_items", ["run_id"], unique=False)
    op.create_index(
        op.f("ix_content_items_source_id"), "content_items", ["source_id"], unique=False
    )
    op.create_index(
        op.f("ix_content_items_triage_route"), "content_items", ["triage_route"], unique=False
    )
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "approval_state",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "withdrawn",
                name="approvalstate",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("approved_by_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "approval_state IN ('pending', 'approved', 'rejected', 'withdrawn')",
            name=op.f("ck_document_versions_approvalstate"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
            name=op.f("fk_document_versions_approved_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_versions_document_id_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["document_versions.id"],
            name=op.f("fk_document_versions_superseded_by_id_document_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
        sa.UniqueConstraint(
            "document_id", "checksum", name=op.f("uq_document_versions_document_id_checksum")
        ),
    )
    op.create_index(
        op.f("ix_document_versions_document_id"), "document_versions", ["document_id"], unique=False
    )
    op.create_table(
        "content_item_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "metrics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name=op.f("fk_content_item_revisions_content_item_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["collection_runs.id"],
            name=op.f("fk_content_item_revisions_run_id_collection_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_item_revisions")),
        sa.UniqueConstraint(
            "content_item_id",
            "revision",
            name=op.f("uq_content_item_revisions_content_item_id_revision"),
        ),
    )
    op.create_index(
        op.f("ix_content_item_revisions_content_item_id"),
        "content_item_revisions",
        ["content_item_id"],
        unique=False,
    )
    op.create_table(
        "mentions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "stance",
            sa.Enum(
                "assert",
                "question",
                "report",
                "sarcasm",
                "unknown",
                name="stance",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("span_start", sa.Integer(), nullable=True),
        sa.Column("span_end", sa.Integer(), nullable=True),
        sa.Column("attached_by_id", sa.Uuid(), nullable=True),
        sa.Column("attach_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "stance IN ('assert', 'question', 'report', 'sarcasm', 'unknown')",
            name=op.f("ck_mentions_stance"),
        ),
        sa.ForeignKeyConstraint(
            ["attached_by_id"],
            ["users.id"],
            name=op.f("fk_mentions_attached_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["claims.id"],
            name=op.f("fk_mentions_claim_id_claims"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name=op.f("fk_mentions_content_item_id_content_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_mentions_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mentions")),
        sa.UniqueConstraint(
            "claim_id", "content_item_id", name=op.f("uq_mentions_claim_id_content_item_id")
        ),
    )
    op.create_index(op.f("ix_mentions_claim_id"), "mentions", ["claim_id"], unique=False)
    op.create_index(
        op.f("ix_mentions_content_item_id"), "mentions", ["content_item_id"], unique=False
    )
    op.create_index(
        op.f("ix_mentions_institution_id"), "mentions", ["institution_id"], unique=False
    )
    op.create_table(
        "passages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_ar_norm", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', coalesce(text, ''))", persisted=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name=op.f("fk_passages_document_version_id_document_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passages")),
        sa.UniqueConstraint(
            "document_version_id", "ordinal", name=op.f("uq_passages_document_version_id_ordinal")
        ),
    )
    op.create_index(
        op.f("ix_passages_document_version_id"), "passages", ["document_version_id"], unique=False
    )
    op.create_index(
        "ix_passages_embedding",
        "passages",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_passages_tsv", "passages", ["tsv"], unique=False, postgresql_using="gin")
    op.create_table(
        "responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "correction",
                "clarification",
                "faq",
                "investigation_notice",
                name="responsekind",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "kind IN ('correction', 'clarification', 'faq', 'investigation_notice')",
            name=op.f("ck_responses_responsekind"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_responses_assessment_id_assessments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_responses_case_id_cases"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_responses_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_responses_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_responses")),
    )
    op.create_index(op.f("ix_responses_case_id"), "responses", ["case_id"], unique=False)
    op.create_index(
        op.f("ix_responses_institution_id"), "responses", ["institution_id"], unique=False
    )
    op.create_table(
        "evidence_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("passage_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.Column(
            "relation",
            sa.Enum(
                "supports",
                "contradicts",
                "context",
                name="evidencerelation",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("relevance_reason", sa.Text(), nullable=False),
        sa.Column("applicability", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relation IN ('supports', 'contradicts', 'context')",
            name=op.f("ck_evidence_links_evidencerelation"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_evidence_links_assessment_id_assessments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name=op.f("fk_evidence_links_document_version_id_document_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"],
            ["evidence_sources.id"],
            name=op.f("fk_evidence_links_evidence_source_id_evidence_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["passage_id"],
            ["passages.id"],
            name=op.f("fk_evidence_links_passage_id_passages"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_links")),
        sa.UniqueConstraint(
            "assessment_id", "passage_id", name=op.f("uq_evidence_links_assessment_id_passage_id")
        ),
    )
    op.create_index(
        op.f("ix_evidence_links_assessment_id"), "evidence_links", ["assessment_id"], unique=False
    )
    op.create_index(
        op.f("ix_evidence_links_passage_id"), "evidence_links", ["passage_id"], unique=False
    )
    op.create_table(
        "response_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column(
            "script",
            sa.Enum("arabic", "latin", name="script", native_enum=False, create_constraint=False),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "citation_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "state",
            sa.Enum(
                "draft",
                "scientific_review",
                "language_review",
                "institutional_review",
                "approved",
                "changes_requested",
                "action_recorded",
                "follow_up",
                "closed",
                name="variantstate",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("ai_generated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "script IN ('arabic', 'latin')", name=op.f("ck_response_variants_script")
        ),
        sa.CheckConstraint(
            "state IN ('draft', 'scientific_review', 'language_review', 'institutional_review', 'approved', 'changes_requested', 'action_recorded', 'follow_up', 'closed')",
            name=op.f("ck_response_variants_variantstate"),
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_response_variants_assessment_id_assessments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_response_variants_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["responses.id"],
            name=op.f("fk_response_variants_response_id_responses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_response_variants")),
        sa.UniqueConstraint(
            "response_id",
            "locale",
            "script",
            "channel",
            name=op.f("uq_response_variants_response_id_locale_script_channel"),
        ),
    )
    op.create_index(
        op.f("ix_response_variants_institution_id"),
        "response_variants",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_response_variants_response_id"), "response_variants", ["response_id"], unique=False
    )
    op.create_table(
        "response_variant_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("response_variant_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "citation_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column("edited_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_response_variant_revisions_assessment_id_assessments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["edited_by_id"],
            ["users.id"],
            name=op.f("fk_response_variant_revisions_edited_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["response_variant_id"],
            ["response_variants.id"],
            name=op.f("fk_response_variant_revisions_response_variant_id_response_variants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_response_variant_revisions")),
        sa.UniqueConstraint(
            "response_variant_id",
            "version",
            name=op.f("uq_response_variant_revisions_response_variant_id_version"),
        ),
    )
    op.create_index(
        op.f("ix_response_variant_revisions_response_variant_id"),
        "response_variant_revisions",
        ["response_variant_id"],
        unique=False,
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("response_variant_id", sa.Uuid(), nullable=False),
        sa.Column("exact_version", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "scientific",
                "language",
                "institutional",
                name="approvalkind",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.Enum(
                "approved",
                "rejected",
                name="approvaldecision",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column("body_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("approver_id", sa.Uuid(), nullable=False),
        sa.Column(
            "approver_role",
            sa.Enum(
                "analyste",
                "referent_scientifique",
                "redacteur",
                "reviseur_linguistique",
                "approbateur",
                "cabinet",
                "partenaire",
                "relais_terrain",
                "administrateur",
                name="approver_role",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidation_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "approver_role IN ('analyste', 'referent_scientifique', 'redacteur', 'reviseur_linguistique', 'approbateur', 'cabinet', 'partenaire', 'relais_terrain', 'administrateur')",
            name=op.f("ck_approvals_approver_role"),
        ),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')", name=op.f("ck_approvals_approvaldecision")
        ),
        sa.CheckConstraint(
            "kind IN ('scientific', 'language', 'institutional')",
            name=op.f("ck_approvals_approvalkind"),
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["users.id"],
            name=op.f("fk_approvals_approver_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_approvals_assessment_id_assessments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_approvals_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["response_variant_id", "exact_version"],
            [
                "response_variant_revisions.response_variant_id",
                "response_variant_revisions.version",
            ],
            name="fk_approvals_variant_revision",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
    )
    op.create_index(
        op.f("ix_approvals_institution_id"), "approvals", ["institution_id"], unique=False
    )
    op.create_index(
        op.f("ix_approvals_response_variant_id"), "approvals", ["response_variant_id"], unique=False
    )
    op.create_table(
        "actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("response_variant_id", sa.Uuid(), nullable=False),
        sa.Column("variant_version", sa.Integer(), nullable=False),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("permitted_reference", sa.Text(), nullable=True),
        sa.Column(
            "follow_up_plan",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_actions_actor_id_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["approvals.id"],
            name=op.f("fk_actions_approval_id_approvals"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_actions_case_id_cases"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_actions_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["response_variant_id", "variant_version"],
            [
                "response_variant_revisions.response_variant_id",
                "response_variant_revisions.version",
            ],
            name="fk_actions_variant_revision",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_actions")),
    )
    op.create_index(op.f("ix_actions_case_id"), "actions", ["case_id"], unique=False)
    op.create_index(op.f("ix_actions_institution_id"), "actions", ["institution_id"], unique=False)
    op.create_index(
        op.f("ix_actions_response_variant_id"), "actions", ["response_variant_id"], unique=False
    )
    op.create_table(
        "follow_ups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.Uuid(), nullable=False),
        sa.Column(
            "horizon",
            sa.Enum(
                "48h",
                "7d",
                "30d",
                name="followupwindow",
                native_enum=False,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled",
                "done",
                "missed",
                "cancelled",
                name="followupstatus",
                native_enum=False,
                create_constraint=False,
            ),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column(
            "observations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("coverage_comparable", sa.Boolean(), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("completed_by_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_scenario", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "horizon IN ('48h', '7d', '30d')", name=op.f("ck_follow_ups_followupwindow")
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'done', 'missed', 'cancelled')",
            name=op.f("ck_follow_ups_followupstatus"),
        ),
        sa.ForeignKeyConstraint(
            ["action_id"],
            ["actions.id"],
            name=op.f("fk_follow_ups_action_id_actions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_id"],
            ["users.id"],
            name=op.f("fk_follow_ups_completed_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_follow_ups_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_follow_ups")),
        sa.UniqueConstraint("action_id", "horizon", name=op.f("uq_follow_ups_action_id_horizon")),
    )
    op.create_index(op.f("ix_follow_ups_action_id"), "follow_ups", ["action_id"], unique=False)
    op.create_index(op.f("ix_follow_ups_due_at"), "follow_ups", ["due_at"], unique=False)
    op.create_index(
        op.f("ix_follow_ups_institution_id"), "follow_ups", ["institution_id"], unique=False
    )

    op.execute(AUDIT_GUARD_FUNCTION)
    op.execute(AUDIT_GUARD_TRIGGER)
    op.execute(AUDIT_GUARD_TRUNCATE)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update_delete ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_append_only()")
    op.drop_table("follow_ups")
    op.drop_table("actions")
    op.drop_table("approvals")
    op.drop_table("response_variant_revisions")
    op.drop_table("response_variants")
    op.drop_table("evidence_links")
    op.drop_table("responses")
    op.drop_table("passages")
    op.drop_table("mentions")
    op.drop_table("content_item_revisions")
    op.drop_table("document_versions")
    op.drop_table("content_items")
    op.drop_table("assessments")
    op.drop_table("membership_roles")
    op.drop_table("documents")
    op.drop_table("collection_runs")
    op.drop_table("claims")
    op.drop_table("case_narratives")
    op.drop_table("alerts")
    op.drop_table("sources")
    op.drop_table("sessions")
    op.drop_table("reports")
    op.drop_table("narratives")
    op.drop_table("memberships")
    op.drop_table("jobs")
    op.drop_table("evidence_sources")
    op.drop_table("cases")
    op.drop_table("users")
    op.drop_table("institutions")
    op.drop_table("audit_events")
