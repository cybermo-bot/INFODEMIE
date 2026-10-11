"""Integration tests against the compose Postgres (database pnsi_test).

Skipped with a clear reason when Postgres is unreachable, unless
PNSI_REQUIRE_DB=1 (make test-api-db), in which case they fail.
Each test runs inside a transaction that is rolled back afterwards.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from pnsi.auth.throttle import login_throttle
from pnsi.cli.seed import seed, seed_email
from pnsi.db import get_db
from pnsi.enums import Role
from pnsi.main import create_app
from pnsi.settings import get_settings

API_DIR = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/integration" in str(item.fspath):
            item.add_marker(pytest.mark.db)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = get_settings().test_database_url
    eng = create_engine(url, future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        eng.dispose()
        reason = f"PostgreSQL unreachable at the test database ({type(exc).__name__})"
        if os.environ.get("PNSI_REQUIRE_DB") == "1":
            pytest.fail(reason)
        pytest.skip(reason + ": run `make services` first")

    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.cmd_opts = type("Opts", (), {"x": [f"db_url={url}"]})()
    # Down then up: proves the downgrade works and starts from a clean schema.
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()


@pytest.fixture
def seeded(db: Session) -> dict[str, str]:
    """ONMNE plus one account per role. Returns {role: password}."""
    passwords = seed(db)
    db.commit()
    return {role.value: passwords[seed_email(role)] for role in Role}


@pytest.fixture
def app(db: Session):
    login_throttle._failures.clear()
    application = create_app()

    def override_db():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    application.dependency_overrides[get_db] = override_db
    return application


@pytest.fixture
def make_client(app):
    def factory() -> TestClient:
        return TestClient(app)

    return factory


def login(client: TestClient, role: Role | str, password: str):
    role = Role(role)
    return client.post("/api/v1/auth/login", json={"email": seed_email(role), "password": password})


def csrf_headers(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("pnsi_csrf", "")}
