"""Server-side sessions in httpOnly cookies, with a CSRF token per session (decision D13)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from pnsi.auth.security import hash_token, new_token
from pnsi.models import User, UserSession
from pnsi.settings import Settings

SESSION_COOKIE = "pnsi_session"
CSRF_COOKIE = "pnsi_csrf"
CSRF_HEADER = "X-CSRF-Token"
# Avoid a write on every request: refresh the idle expiry at most this often.
TOUCH_INTERVAL = timedelta(minutes=5)


@dataclass
class IssuedSession:
    session: UserSession
    token: str
    csrf_token: str


def utcnow() -> datetime:
    return datetime.now(UTC)


def _ua_hash(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    return hashlib.sha256(user_agent.encode()).hexdigest()


def create_session(
    db: Session, user: User, settings: Settings, user_agent: str | None = None
) -> IssuedSession:
    key = settings.secret_key.get_secret_value()
    token, csrf = new_token(), new_token()
    now = utcnow()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token, key),
        csrf_token_hash=hash_token(csrf, key),
        last_seen_at=now,
        expires_at=now + timedelta(hours=settings.session_idle_hours),
        user_agent_hash=_ua_hash(user_agent),
    )
    db.add(session)
    db.flush()
    return IssuedSession(session, token, csrf)


def resolve_session(db: Session, token: str | None, settings: Settings) -> UserSession | None:
    """The live session for a cookie token, or None. Extends the idle expiry."""
    if not token:
        return None
    key = settings.secret_key.get_secret_value()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token, key)))
    if session is None or session.revoked_at is not None:
        return None
    now = utcnow()
    hard_limit = session.created_at + timedelta(hours=settings.session_max_hours)
    if session.expires_at <= now or hard_limit <= now:
        return None
    if now - session.last_seen_at > TOUCH_INTERVAL:
        session.last_seen_at = now
        session.expires_at = min(now + timedelta(hours=settings.session_idle_hours), hard_limit)
    return session


def revoke_session(session: UserSession) -> None:
    session.revoked_at = utcnow()


def set_session_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    max_age = settings.session_max_hours * 3600
    common = {"path": "/", "samesite": "lax", "secure": settings.secure_cookies, "max_age": max_age}
    response.set_cookie(SESSION_COOKIE, issued.token, httponly=True, **common)
    # Readable by the web app, which echoes it in the X-CSRF-Token header.
    response.set_cookie(CSRF_COOKIE, issued.csrf_token, httponly=False, **common)


def clear_session_cookies(response: Response, settings: Settings) -> None:
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", secure=settings.secure_cookies, samesite="lax")
