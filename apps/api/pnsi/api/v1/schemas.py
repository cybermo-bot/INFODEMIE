"""Request and response models for identity, users and audit endpoints."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission, nav_for
from pnsi.enums import Locale, Role
from pnsi.models import Institution, Membership, User

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email_syntax(value: str) -> str:
    # Syntax only: dev accounts use the reserved .local domain (seed), which
    # strict validators reject. Deliverability is not our concern here.
    value = value.strip().lower()
    if not _EMAIL.match(value):
        raise ValueError("adresse e-mail invalide")
    return value


Email = Annotated[str, Field(min_length=3, max_length=320), AfterValidator(_email_syntax)]


class LoginIn(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=256)


class InstitutionOut(BaseModel):
    id: uuid.UUID
    code: str
    name_fr: str
    name_ar: str | None
    name_en: str | None


class NavItemOut(BaseModel):
    key: str
    path: str
    stage: int


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    locale: Locale
    version: int
    institution: InstitutionOut
    roles: list[Role]
    permissions: list[Permission]
    nav: list[NavItemOut]

    @classmethod
    def build(cls, user: User, institution: Institution, principal: Principal) -> MeOut:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            locale=user.locale,
            version=user.version,
            institution=InstitutionOut.model_validate(institution, from_attributes=True),
            roles=sorted(principal.roles),
            permissions=sorted(principal.permissions),
            nav=[
                NavItemOut(key=n.key, path=n.path, stage=n.stage)
                for n in nav_for(principal.permissions)
            ],
        )


class MePatch(BaseModel):
    locale: Locale
    expected_version: int = Field(ge=1)


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    locale: Locale
    is_active: bool
    roles: list[Role]
    created_at: datetime

    @classmethod
    def build(cls, membership: Membership) -> MemberOut:
        user = membership.user
        return cls(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            locale=user.locale,
            is_active=user.is_active and membership.is_active,
            roles=sorted(r.role for r in membership.roles),
            created_at=user.created_at,
        )


class MemberCreate(BaseModel):
    email: Email
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=256)
    roles: list[Role] = Field(min_length=1)
    locale: Locale = Locale.FR
    justification: str | None = Field(default=None, max_length=500)


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    actor_id: uuid.UUID | None
    actor_roles: list[str]
    action: str
    object_type: str | None
    object_id: str | None
    changes: dict[str, Any]
    context: dict[str, Any]
    request_id: str | None


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    next_cursor: int | None
