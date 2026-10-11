"""Login, logout and the current user."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from pnsi.api.v1.schemas import LoginIn, MeOut, MePatch
from pnsi.auth.deps import CurrentPrincipal, SettingsDep, allowed_origins
from pnsi.auth.security import origin_allowed
from pnsi.auth.sessions import clear_session_cookies, set_session_cookies
from pnsi.auth.throttle import login_throttle
from pnsi.db import DbSession
from pnsi.errors import ERROR_RESPONSES, Forbidden, NotFound, TooManyRequests, Unauthenticated
from pnsi.models import Institution, User
from pnsi.services import auth as auth_service
from pnsi.services import users as user_service

router = APIRouter(tags=["auth"], responses=ERROR_RESPONSES)


@router.post("/auth/login", response_model=MeOut, operation_id="login")
def login(
    body: LoginIn, request: Request, response: Response, db: DbSession, settings: SettingsDep
) -> MeOut:
    if not origin_allowed(request.headers.get("origin"), allowed_origins(settings)):
        raise Forbidden(code="origin_rejected", message="Origine de la requête refusée.")
    result = auth_service.login(
        db,
        body.email,
        body.password,
        settings,
        login_throttle,
        user_agent=request.headers.get("user-agent"),
    )
    if not result.ok:
        # Keep the audit event of the failed attempt even though the request fails.
        db.commit()
        if result.retry_after is not None:
            raise TooManyRequests(headers={"Retry-After": str(result.retry_after)})
        raise Unauthenticated(code="invalid_credentials", message="Identifiants incorrects.")
    assert result.user and result.principal and result.issued
    set_session_cookies(response, result.issued, settings)
    institution = db.get(Institution, result.principal.institution_id)
    assert institution is not None
    return MeOut.build(result.user, institution, result.principal)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, operation_id="logout")
def logout(principal: CurrentPrincipal, db: DbSession, settings: SettingsDep) -> Response:
    auth_service.logout(db, principal)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookies(response, settings)
    return response


def _me(db: DbSession, principal: CurrentPrincipal) -> MeOut:
    user = db.get(User, principal.user_id)
    institution = db.get(Institution, principal.institution_id)
    if user is None or institution is None:
        raise NotFound()
    return MeOut.build(user, institution, principal)


@router.get("/me", response_model=MeOut, operation_id="get_me")
def get_me(principal: CurrentPrincipal, db: DbSession) -> MeOut:
    return _me(db, principal)


@router.patch("/me", response_model=MeOut, operation_id="update_me")
def update_me(body: MePatch, principal: CurrentPrincipal, db: DbSession) -> MeOut:
    user_service.update_own_locale(db, principal, body.locale, body.expected_version)
    return _me(db, principal)
