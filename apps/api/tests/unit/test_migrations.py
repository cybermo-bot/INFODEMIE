"""The hand-completed migration renders and matches the models (offline, no database)."""

import io
import re
from contextlib import redirect_stdout
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import pnsi.models  # noqa: F401
from pnsi.models.base import Base

API_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.cmd_opts = type("Opts", (), {"x": ["db_url=postgresql+psycopg://offline:x@localhost/x"]})()
    return cfg


def offline_sql() -> str:
    buf = io.StringIO()
    cfg = alembic_config()
    cfg.output_buffer = buf
    with redirect_stdout(buf):
        command.upgrade(cfg, "head", sql=True)
    return buf.getvalue()


def test_single_head():
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_upgrade_renders_every_table():
    sql = offline_sql()
    created = set(re.findall(r"CREATE TABLE (\w+)", sql))
    assert set(Base.metadata.tables) <= created


def test_migration_constraints_match_models():
    sql = offline_sql()
    dialect = postgresql.dialect()
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect))
        for name in re.findall(r"CONSTRAINT (\S+)", ddl):
            assert f"CONSTRAINT {name} " in sql, f"migration lacks {name}"
        for idx in table.indexes:
            assert f"INDEX {idx.name} " in sql, f"migration lacks index {idx.name}"


def test_migration_check_constraint_count_matches_models():
    sql = offline_sql()
    dialect = postgresql.dialect()
    model_checks = sum(
        str(CreateTable(t).compile(dialect=dialect)).count(" CHECK ")
        for t in Base.metadata.sorted_tables
    )
    assert sql.count(" CHECK ") == model_checks


def test_audit_events_are_append_only_in_database():
    sql = offline_sql()
    assert "BEFORE UPDATE OR DELETE ON audit_events" in sql
    assert "BEFORE TRUNCATE ON audit_events" in sql


def test_extensions_created():
    sql = offline_sql()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
