"""Schema rules from spec §14 and CLAUDE.md, checked on the metadata (no database)."""

import re

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import pnsi.models  # noqa: F401
from pnsi.models.base import Base

TABLES = Base.metadata.tables

# Append-only or immutable tables: rows are inserted, never updated.
IMMUTABLE = {
    "audit_events",
    "content_item_revisions",
    "response_variant_revisions",
    "evidence_links",
    "passages",
    "membership_roles",
    "case_narratives",
}

EXPECTED_TABLES = {
    "institutions", "users", "memberships", "membership_roles", "sessions",
    "sources", "collection_runs", "content_items", "content_item_revisions",
    "claims", "mentions", "cases", "narratives", "case_narratives",
    "evidence_sources", "documents", "document_versions", "passages",
    "assessments", "evidence_links", "responses", "response_variants",
    "response_variant_revisions", "approvals", "actions", "follow_ups",
    "alerts", "reports", "audit_events", "jobs",
}  # fmt: skip


def test_build_plan_tables_exist():
    assert set(TABLES) >= EXPECTED_TABLES


def test_every_mutable_table_has_timestamps_and_version():
    for name, table in TABLES.items():
        if name in IMMUTABLE:
            continue
        cols = table.c
        for col in ("created_at", "updated_at", "version"):
            assert col in cols, f"{name} lacks {col}"
            assert not cols[col].nullable, f"{name}.{col} must be NOT NULL"


def test_immutable_tables_cannot_look_mutable():
    for name in IMMUTABLE - {"case_narratives"}:
        assert "updated_at" not in TABLES[name].c, name
        assert "version" not in TABLES[name].c or name == "response_variant_revisions", name


def test_timestamps_are_timezone_aware():
    for name, table in TABLES.items():
        for col in table.c:
            if col.name.endswith("_at"):
                assert getattr(col.type, "timezone", False), (
                    f"{name}.{col.name} must be timestamptz"
                )


def test_content_items_record_route_source_run_and_scenario_flag():
    cols = TABLES["content_items"].c
    for name in ("route", "source_id", "run_id", "is_scenario"):
        assert name in cols
        assert not cols[name].nullable, name
    assert cols["route"].type.enums == ["official", "assisted", "public_contested", "internal"]


def test_content_items_store_no_raw_platform_identifiers():
    cols = set(TABLES["content_items"].c.keys())
    forbidden = {"author", "author_name", "author_handle", "handle", "username", "profile_url"}
    assert not cols & forbidden
    assert "external_id_hash" in cols and "external_id" not in cols


def test_scenario_flag_on_demo_relevant_tables():
    for name in (
        "content_items", "claims", "cases", "narratives", "assessments",
        "responses", "actions", "follow_ups", "alerts", "reports",
    ):  # fmt: skip
        col = TABLES[name].c["is_scenario"]
        assert not col.nullable and col.server_default is not None


def test_institution_scope_on_operational_tables():
    shared = {"institutions", "users", "sessions", "membership_roles", "case_narratives",
              "evidence_sources", "documents", "document_versions", "passages",
              "evidence_links", "content_item_revisions", "response_variant_revisions",
              "audit_events", "jobs"}  # fmt: skip
    for name, table in TABLES.items():
        if name in shared:
            continue
        assert "institution_id" in table.c, f"{name} needs institution_id for scoped access"


def test_approvals_and_actions_bind_exact_variant_revision():
    for table, cols in (
        ("approvals", ["response_variant_id", "exact_version"]),
        ("actions", ["response_variant_id", "variant_version"]),
    ):
        fks = [fk for fk in TABLES[table].foreign_key_constraints if fk.column_keys == cols]
        assert fks, f"{table} must reference response_variant_revisions by (id, version)"
        assert fks[0].referred_table.name == "response_variant_revisions"


def test_follow_ups_unique_per_action_and_window():
    uniques = [
        tuple(c.name for c in con.columns)
        for con in TABLES["follow_ups"].constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ("action_id", "window") in uniques


def test_content_items_idempotent_per_source():
    uniques = [
        tuple(c.name for c in con.columns)
        for con in TABLES["content_items"].constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ("source_id", "external_id_hash") in uniques


def test_constraint_and_index_names_fit_postgres():
    dialect = postgresql.dialect()
    seen: set[str] = set()
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect))
        names = re.findall(r"CONSTRAINT (\S+)", ddl)
        names += [idx.name for idx in table.indexes]
        for idx in table.indexes:
            str(CreateIndex(idx).compile(dialect=dialect))
        for name in names:
            assert len(name) <= 63, name
            assert name not in seen, f"duplicate constraint name {name}"
            seen.add(name)


def test_passages_have_vector_and_full_text_columns():
    cols = TABLES["passages"].c
    assert cols["embedding"].type.dim == 1024
    assert cols["tsv"].computed is not None
