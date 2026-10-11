"""Login and logout. Both outcomes of a login attempt are audited."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pnsi.audit import service as audit
from pnsi.auth.deps import principal_for
from pnsi.auth.principal import Principal
from pnsi.auth.security import hash_password, needs_rehash, verify_password
from pnsi.auth.sessions import IssuedSession, create_session, revoke_session, utcnow
from pnsi.auth.throttle import LoginThrottle
from pnsi.models import User, UserSession
from pnsi.settings import Settings


@dataclass
class LoginResult:
    ok: bool
    user: User | None = None
    principal: Principal | None = None
    issued: IssuedSession | None = None
    retry_after: int | None = None
    reason: str | None = None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_fingerprint(email: str) -> str:
    """Audit and throttle key for an attempted login. Never the raw address."""
    return hashlib.sha256(normalize_email(email).encode()).hexdigest()[:16]


def login(
    db: Session,
    email: str,
    password: str,
    settings: Settings,
    throttle: LoginThrottle,
    user_agent: str | None = None,
) -> LoginResult:
    fingerprint = email_fingerprint(email)
    retry = throttle.retry_after(fingerprint)
    if retry is not None:
        audit.record(db, "auth.login_throttled", context={"email_fingerprint": fingerprint})
        return LoginResult(ok=False, retry_after=retry, reason="throttled")

    user = db.scalar(select(User).where(func.lower(User.email) == normalize_email(email)))
    valid = verify_password(user.password_hash if user else None, password)
    principal = principal_for(db, user) if (user and valid and user.is_active) else None

    if principal is None:
        throttle.record_failure(fingerprint)
        reason = "bad_credentials" if not (user and valid) else "inactive_or_no_membership"
        audit.record(
            db,
            "auth.login_failed",
            actor_id=user.id if user and valid else None,
            context={"email_fingerprint": fingerprint, "reason": reason},
        )
        return LoginResult(ok=False, reason=reason)

    assert user is not None
    throttle.reset(fingerprint)
    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    issued = create_session(db, user, settings, user_agent)
    principal = Principal.build(
        principal.user_id, principal.institution_id, principal.roles, issued.session.id
    )
    audit.record(
        db,
        "auth.login",
        actor=principal,
        object_type="session",
        object_id=issued.session.id,
    )
    return LoginResult(ok=True, user=user, principal=principal, issued=issued)


def logout(db: Session, principal: Principal) -> None:
    if principal.session_id is None:
        return
    session = db.get(UserSession, principal.session_id)
    if session is not None and session.revoked_at is None:
        revoke_session(session)
        audit.record(
            db, "auth.logout", actor=principal, object_type="session", object_id=session.id
        )
