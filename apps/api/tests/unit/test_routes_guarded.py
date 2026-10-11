"""Route guards with the principal injected (no database). DB-backed versions live in
tests/integration."""

import uuid

import pytest
from fastapi.testclient import TestClient

from pnsi.auth.deps import get_principal
from pnsi.auth.principal import Principal
from pnsi.db import get_db
from pnsi.enums import Role
from pnsi.main import create_app


class NoDb:
    def __getattr__(self, name):
        raise AssertionError("route touched the database before checking permissions")


def client_as(role: Role | None) -> TestClient:
    app = create_app()

    def fake_db():
        yield NoDb()

    app.dependency_overrides[get_db] = fake_db
    if role is not None:
        principal = Principal.build(uuid.uuid4(), uuid.uuid4(), frozenset({role}))
        app.dependency_overrides[get_principal] = lambda: principal
    return TestClient(app)


@pytest.mark.parametrize("role", [r for r in Role if r is not Role.ADMINISTRATEUR])
def test_audit_read_forbidden_for_non_admin(role):
    res = client_as(role).get("/api/v1/audit-events")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("path", ["/api/v1/users", "/api/v1/audit-events"])
def test_analyst_cannot_reach_admin_routes(path):
    assert client_as(Role.ANALYSTE).get(path).status_code == 403


def test_create_user_forbidden_for_analyst():
    res = client_as(Role.ANALYSTE).post(
        "/api/v1/users",
        json={"email": "x@pnsi.local", "display_name": "X", "password": "a" * 12,
              "roles": ["cabinet"]},
    )  # fmt: skip
    assert res.status_code == 403


def test_unauthenticated_without_cookie():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([NoDb()])

    # No session cookie: the resolver returns before any query.
    res = TestClient(app).get("/api/v1/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthenticated"


def test_foreign_origin_rejected():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([NoDb()])
    res = TestClient(app).post(
        "/api/v1/auth/login",
        json={"email": "a@pnsi.local", "password": "x"},
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "origin_rejected"


def test_login_validation_error_shape():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: iter([NoDb()])
    res = TestClient(app).post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert res.status_code == 422
    fields = {f["field"] for f in res.json()["error"]["field_errors"]}
    assert {"email", "password"} <= fields
