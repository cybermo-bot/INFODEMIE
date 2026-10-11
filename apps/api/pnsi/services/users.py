"""User and membership management, scoped to the caller's institution."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from pnsi.audit import service as audit
from pnsi.auth.principal import Principal
from pnsi.auth.security import hash_password
from pnsi.authz.permissions import SENSITIVE_ROLES, Permission
from pnsi.authz.service import ensure_permission
from pnsi.enums import Locale, Role
from pnsi.errors import ApiError, Conflict, FieldError, Forbidden, NotFound
from pnsi.models import Membership, MembershipRole, User
from pnsi.services.auth import normalize_email


class EmailTaken(ApiError):
    status_code = 409
    code = "email_taken"
    message = "Cette adresse est déjà utilisée."


def get_membership(db: Session, user_id: uuid.UUID, institution_id: uuid.UUID) -> Membership | None:
    return db.scalar(
        select(Membership)
        .where(Membership.user_id == user_id, Membership.institution_id == institution_id)
        .options(selectinload(Membership.roles), selectinload(Membership.user))
    )


def list_members(db: Session, principal: Principal) -> Sequence[Membership]:
    ensure_permission(principal, Permission.USERS_MANAGE)
    return db.scalars(
        select(Membership)
        .where(Membership.institution_id == principal.institution_id)
        .options(selectinload(Membership.roles), selectinload(Membership.user))
        .order_by(Membership.created_at)
    ).all()


def get_member(db: Session, principal: Principal, user_id: uuid.UUID) -> Membership:
    ensure_permission(principal, Permission.USERS_MANAGE)
    membership = get_membership(db, user_id, principal.institution_id)
    if membership is None:
        # Users of other institutions are invisible, not forbidden (no existence leak).
        raise NotFound()
    return membership


def check_role_grant(principal: Principal, target_user_id: uuid.UUID | None, roles: set[Role],
                     justification: str | None) -> None:  # fmt: skip
    """Spec §3: an administrator cannot silently grant scientific or approval authority."""
    sensitive = roles & SENSITIVE_ROLES
    if not sensitive:
        return
    if target_user_id is not None and target_user_id == principal.user_id:
        raise Forbidden(
            code="self_grant_forbidden",
            message="Un rôle scientifique ou d'approbation ne peut pas être attribué à soi-même.",
        )
    if not justification or len(justification.strip()) < 10:
        raise ApiError(
            "Une justification écrite est requise pour ce rôle.",
            code="justification_required",
            field_errors=[FieldError(field="justification", message="Au moins 10 caractères.")],
        )


def create_member(
    db: Session,
    principal: Principal,
    *,
    email: str,
    display_name: str,
    password: str,
    roles: set[Role],
    locale: Locale = Locale.FR,
    justification: str | None = None,
) -> Membership:
    ensure_permission(principal, Permission.USERS_MANAGE)
    check_role_grant(principal, None, roles, justification)
    email = normalize_email(email)
    if db.scalar(select(func.count()).select_from(User).where(User.email == email)):
        raise EmailTaken()

    user = User(
        email=email,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        locale=locale,
    )
    db.add(user)
    db.flush()
    membership = Membership(user_id=user.id, institution_id=principal.institution_id)
    membership.roles = [
        MembershipRole(role=r, granted_by_id=principal.user_id, justification=justification)
        for r in sorted(roles)
    ]
    db.add(membership)
    db.flush()
    audit.record(
        db,
        "user.created",
        actor=principal,
        object_type="user",
        object_id=user.id,
        changes={
            "display_name": {"from": None, "to": user.display_name},
            "roles": {"from": [], "to": sorted(r.value for r in roles)},
        },
        context={"justification": justification} if justification else None,
    )
    return membership


def update_own_locale(
    db: Session, principal: Principal, locale: Locale, expected_version: int
) -> User:
    user = db.get(User, principal.user_id)
    if user is None:
        raise NotFound()
    if user.version != expected_version:
        raise Conflict()
    if user.locale != locale:
        before = user.locale
        user.locale = locale
        db.flush()
        audit.record(
            db,
            "user.locale_changed",
            actor=principal,
            object_type="user",
            object_id=user.id,
            changes=audit.diff({"locale": before}, {"locale": locale}),
        )
    return user
