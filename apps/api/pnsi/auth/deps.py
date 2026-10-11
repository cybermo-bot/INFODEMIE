"""FastAPI dependencies: the current principal and permission guards."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pnsi.auth.principal import Principal
from pnsi.auth.security import csrf_valid, origin_allowed
from pnsi.auth.sessions import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, resolve_session
from pnsi.authz.permissions import Permission
from pnsi.authz.service import ensure_permission
from pnsi.db import DbSession
from pnsi.errors import Forbidden, Unauthenticated
from pnsi.models import Membership, User
from pnsi.settings import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


def allowed_origins(settings: Settings) -> set[str]:
    return {settings.app_base_url, settings.api_base_url}


def active_membership(db: Session, user: User) -> Membership | None:
    """The user's working institution: the oldest active membership.

    Switching between several institutions comes with the pilot (OIDC).
    """
    return db.scalar(
        select(Membership)
        .where(Membership.user_id == user.id, Membership.is_active.is_(True))
        .options(selectinload(Membership.roles), selectinload(Membership.institution))
        .order_by(Membership.created_at)
        .limit(1)
    )


def principal_for(db: Session, user: User, session_id=None) -> Principal | None:
    membership = active_membership(db, user)
    if membership is None or not membership.institution.is_active:
        return None
    roles = frozenset(r.role for r in membership.roles)
    return Principal.build(user.id, membership.institution_id, roles, session_id)


def get_principal(request: Request, db: DbSession, settings: SettingsDep) -> Principal:
    if not origin_allowed(request.headers.get("origin"), allowed_origins(settings)):
        raise Forbidden(code="origin_rejected", message="Origine de la requête refusée.")

    session = resolve_session(db, request.cookies.get(SESSION_COOKIE), settings)
    if session is None:
        raise Unauthenticated()

    if not csrf_valid(
        request.method,
        request.headers.get(CSRF_HEADER),
        request.cookies.get(CSRF_COOKIE),
        session.csrf_token_hash,
        settings.secret_key.get_secret_value(),
    ):
        raise Forbidden(code="csrf_failed", message="Jeton CSRF absent ou invalide.")

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise Unauthenticated()
    principal = principal_for(db, user, session.id)
    if principal is None:
        raise Forbidden(code="no_membership", message="Aucune affectation active.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def require(permission: Permission) -> Callable[[Principal], Principal]:
    def guard(principal: CurrentPrincipal) -> Principal:
        ensure_permission(principal, permission)
        return principal

    guard.__name__ = f"require_{permission.value.replace('.', '_')}"
    return guard
