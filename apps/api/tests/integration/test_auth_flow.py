"""Stage 1 acceptance: roles, menus, 403s, CSRF and audit, through direct API calls."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import StaleDataError

from pnsi.authz.permissions import nav_for, permissions_for
from pnsi.enums import Role
from pnsi.models import AuditEvent, Institution, Membership, MembershipRole, User, UserSession
from tests.integration.conftest import csrf_headers, login


def audit_actions(db) -> list[str]:
    return list(db.scalars(select(AuditEvent.action).order_by(AuditEvent.id)))


@pytest.mark.parametrize("role", list(Role))
def test_each_seeded_role_logs_in_and_sees_its_menu(role, seeded, make_client):
    client = make_client()
    res = login(client, role, seeded[role.value])
    assert res.status_code == 200, res.text
    assert "pnsi_session" in client.cookies and "pnsi_csrf" in client.cookies
    me = client.get("/api/v1/me").json()
    assert me["roles"] == [role.value]
    expected = [n.key for n in nav_for(permissions_for([role]))]
    assert [n["key"] for n in me["nav"]] == expected


def test_session_cookie_is_http_only(seeded, make_client):
    client = make_client()
    res = login(client, Role.ANALYSTE, seeded["analyste"])
    cookies = res.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith("pnsi_session="))
    csrf_cookie = next(c for c in cookies if c.startswith("pnsi_csrf="))
    assert "HttpOnly" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "samesite=lax" in session_cookie.lower()


def test_only_token_hashes_are_stored(db, seeded, make_client):
    client = make_client()
    login(client, Role.ANALYSTE, seeded["analyste"])
    token = client.cookies["pnsi_session"]
    stored = db.scalars(select(UserSession.token_hash)).all()
    assert stored and token not in stored


def test_forbidden_api_call_returns_403(seeded, make_client):
    client = make_client()
    login(client, Role.ANALYSTE, seeded["analyste"])
    res = client.get("/api/v1/audit-events")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "forbidden"


def test_cabinet_cannot_create_users(seeded, make_client):
    client = make_client()
    login(client, Role.CABINET, seeded["cabinet"])
    res = client.post(
        "/api/v1/users",
        json={"email": "n@pnsi.local", "display_name": "N", "password": "p" * 14,
              "roles": ["analyste"]},
        headers=csrf_headers(client),
    )  # fmt: skip
    assert res.status_code == 403


def test_login_is_audited_success_and_failure(db, seeded, make_client):
    client = make_client()
    assert login(client, Role.ANALYSTE, "wrong-password").status_code == 401
    assert login(client, Role.ANALYSTE, seeded["analyste"]).status_code == 200
    actions = audit_actions(db)
    assert "auth.login_failed" in actions
    assert "auth.login" in actions
    failed = db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.login_failed"))
    assert "analyste@pnsi.local" not in str(failed.context)


def test_unknown_account_and_wrong_password_look_the_same(seeded, make_client):
    client = make_client()
    a = client.post("/api/v1/auth/login", json={"email": "nobody@pnsi.local", "password": "x"})
    b = login(client, Role.ANALYSTE, "wrong")
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["code"] == b.json()["error"]["code"]


def test_throttle_after_repeated_failures(seeded, make_client):
    client = make_client()
    codes = [login(client, Role.CABINET, "bad").status_code for _ in range(6)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
    # Even the right password waits until the window passes.
    assert login(client, Role.CABINET, seeded["cabinet"]).status_code == 429


def test_unsafe_request_needs_csrf(seeded, make_client):
    client = make_client()
    me = login(client, Role.ANALYSTE, seeded["analyste"]).json()
    body = {"locale": "ar", "expected_version": me["version"]}
    res = client.patch("/api/v1/me", json=body)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "csrf_failed"
    res = client.patch("/api/v1/me", json=body, headers=csrf_headers(client))
    assert res.status_code == 200
    assert res.json()["locale"] == "ar"


def test_update_is_audited_and_version_checked(db, seeded, make_client):
    client = make_client()
    me = login(client, Role.ANALYSTE, seeded["analyste"]).json()
    res = client.patch(
        "/api/v1/me", json={"locale": "en", "expected_version": me["version"]},
        headers=csrf_headers(client),
    )  # fmt: skip
    assert res.status_code == 200
    assert res.json()["version"] == me["version"] + 1
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "user.locale_changed"))
    assert event.changes == {"locale": {"from": "fr", "to": "en"}}
    stale = client.patch(
        "/api/v1/me", json={"locale": "ar", "expected_version": me["version"]},
        headers=csrf_headers(client),
    )  # fmt: skip
    assert stale.status_code == 409


def test_admin_creates_user_and_it_is_audited(db, seeded, make_client):
    client = make_client()
    login(client, Role.ADMINISTRATEUR, seeded["administrateur"])
    res = client.post(
        "/api/v1/users",
        json={"email": "Nouvel.Analyste@pnsi.local", "display_name": "Compte de test",
              "password": "p" * 14, "roles": ["analyste"]},
        headers=csrf_headers(client),
    )  # fmt: skip
    assert res.status_code == 201, res.text
    assert res.json()["email"] == "nouvel.analyste@pnsi.local"
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "user.created",
                                              AuditEvent.actor_id.is_not(None)))  # fmt: skip
    assert event.object_id == res.json()["user_id"]
    assert "password" not in str(event.changes).lower() or "***" in str(event.changes)

    audit_page = client.get("/api/v1/audit-events").json()
    assert any(e["action"] == "user.created" for e in audit_page["items"])


def test_sensitive_role_needs_justification(seeded, make_client):
    client = make_client()
    login(client, Role.ADMINISTRATEUR, seeded["administrateur"])
    body = {"email": "ref@pnsi.local", "display_name": "R", "password": "p" * 14,
            "roles": ["referent_scientifique"]}  # fmt: skip
    res = client.post("/api/v1/users", json=body, headers=csrf_headers(client))
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "justification_required"
    body["justification"] = "Référent DSSB désigné par note de service."
    res = client.post("/api/v1/users", json=body, headers=csrf_headers(client))
    assert res.status_code == 201


def test_other_institution_cannot_see_onmne_users(db, seeded, make_client):
    from pnsi.auth.security import hash_password

    other = Institution(code="AUTRE", name_fr="Institution de test")
    db.add(other)
    db.flush()
    admin = User(email="admin@autre.local", display_name="Admin test",
                 password_hash=hash_password("autre-password-123"))  # fmt: skip
    db.add(admin)
    db.flush()
    m = Membership(user_id=admin.id, institution_id=other.id)
    m.roles = [MembershipRole(role=Role.ADMINISTRATEUR)]
    db.add(m)
    db.commit()

    onmne_user = db.scalar(select(User).where(User.email == "analyste@pnsi.local"))
    client = make_client()
    res = client.post(
        "/api/v1/auth/login", json={"email": "admin@autre.local", "password": "autre-password-123"}
    )
    assert res.status_code == 200
    assert client.get(f"/api/v1/users/{onmne_user.id}").status_code == 404
    listed = {u["email"] for u in client.get("/api/v1/users").json()}
    assert listed == {"admin@autre.local"}
    events = client.get("/api/v1/audit-events").json()["items"]
    assert all(e["actor_id"] in (None, str(admin.id)) for e in events)


def test_logout_revokes_session(db, seeded, make_client):
    client = make_client()
    login(client, Role.ANALYSTE, seeded["analyste"])
    token = client.cookies["pnsi_session"]
    assert client.post("/api/v1/auth/logout", headers=csrf_headers(client)).status_code == 204
    client.cookies.set("pnsi_session", token)
    assert client.get("/api/v1/me").status_code == 401
    assert "auth.logout" in audit_actions(db)


def test_audit_events_cannot_be_updated_or_deleted(db, seeded):
    event_id = db.scalar(select(AuditEvent.id).limit(1))
    for statement in (
        "UPDATE audit_events SET action = 'tampered' WHERE id = :id",
        "DELETE FROM audit_events WHERE id = :id",
    ):
        nested = db.begin_nested()
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(statement), {"id": event_id})
        nested.rollback()


def test_stale_write_raises(db, seeded):
    user = db.scalar(select(User).where(User.email == "cabinet@pnsi.local"))
    db.execute(text("UPDATE users SET version = version + 1 WHERE id = :id"), {"id": user.id})
    user.display_name = "Changed"
    with pytest.raises(StaleDataError):
        db.flush()
