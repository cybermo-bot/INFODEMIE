from fastapi.testclient import TestClient

from pnsi.api.v1 import health
from pnsi.main import create_app


def client() -> TestClient:
    return TestClient(create_app())


def test_live_needs_nothing():
    res = client().get("/api/v1/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    assert res.headers["X-Request-ID"]


def test_health_reports_failures_visibly(monkeypatch):
    monkeypatch.setattr(health, "check_database", lambda: "en_echec")
    monkeypatch.setattr(health, "check_redis", lambda: "ok")
    res = client().get("/api/v1/health")
    assert res.status_code == 503
    assert res.json() == {"status": "degrade", "database": "en_echec", "redis": "ok"}


def test_health_ok(monkeypatch):
    monkeypatch.setattr(health, "check_database", lambda: "ok")
    monkeypatch.setattr(health, "check_redis", lambda: "ok")
    assert client().get("/api/v1/health").json()["status"] == "ok"


def test_unknown_route_uses_error_shape():
    res = client().get("/api/v1/nope", headers={"X-Request-ID": "req-12345678"})
    assert res.status_code == 404
    body = res.json()["error"]
    assert body["code"] == "not_found"
    assert body["request_id"] == "req-12345678"
