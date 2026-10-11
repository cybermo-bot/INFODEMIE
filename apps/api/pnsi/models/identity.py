"""Institutions, users, memberships with scoped roles, and login sessions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pnsi.enums import Locale, Role
from pnsi.models.base import Base, CreatedAt, Mutable, UUIDPk, str_enum, user_fk


class Institution(UUIDPk, Mutable, Base):
    __tablename__ = "institutions"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name_fr: Mapped[str] = mapped_column(String(255))
    name_ar: Mapped[str | None] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class User(UUIDPk, Mutable, Base):
    __tablename__ = "users"

    # Stored lowercased by the service layer.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    # Null for accounts that will only use institutional OIDC (pilot).
    password_hash: Mapped[str | None] = mapped_column(String(255))
    locale: Mapped[Locale] = mapped_column(
        str_enum(Locale), default=Locale.FR, server_default=Locale.FR.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None]

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", foreign_keys="Membership.user_id"
    )


class Membership(UUIDPk, Mutable, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "institution_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    user: Mapped[User] = relationship(back_populates="memberships", foreign_keys=[user_id])
    institution: Mapped[Institution] = relationship()
    roles: Mapped[list[MembershipRole]] = relationship(
        back_populates="membership", cascade="all, delete-orphan"
    )


class MembershipRole(UUIDPk, CreatedAt, Base):
    """One role held through a membership. Small teams may combine roles (spec §3).

    Rows are added or removed, never edited; both are audited.
    """

    __tablename__ = "membership_roles"
    __table_args__ = (UniqueConstraint("membership_id", "role"),)

    membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(str_enum(Role))
    granted_by_id: Mapped[uuid.UUID | None] = user_fk()
    justification: Mapped[str | None] = mapped_column(String(500))

    membership: Mapped[Membership] = relationship(back_populates="roles")


class UserSession(UUIDPk, Mutable, Base):
    """Server-side session (decision D13). Only hashes of the tokens are stored."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    last_seen_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship()
