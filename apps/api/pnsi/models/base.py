"""Declarative base, naming convention and shared column mixins."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, MetaData, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Stable constraint names so hand-written migrations and `alembic check` agree.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        datetime: DateTime(timezone=True),
        uuid.UUID: Uuid(as_uuid=True),
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
    }


def str_enum(enum_cls: type[StrEnum], name: str | None = None) -> Enum:
    """Store an enum as varchar with a CHECK constraint on its values."""
    return Enum(
        enum_cls,
        name=name or enum_cls.__name__.lower(),
        native_enum=False,
        create_constraint=True,
        length=max(len(m.value) for m in enum_cls),
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class UUIDPk:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, sort_order=-100)


class CreatedAt:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, sort_order=100
    )


class Mutable(CreatedAt):
    """created_at, updated_at and an optimistic-lock version (spec §14).

    SQLAlchemy increments `version` on every UPDATE and raises StaleDataError
    when the row changed underneath; the API turns that into 409.
    """

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False, sort_order=101
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1", sort_order=102
    )

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:  # noqa: N805
        return {"version_id_col": cls.__table__.c.version}


class Scenario:
    """Scenario rows are demo data, shown with the label "Scénario de démonstration"."""

    is_scenario: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", sort_order=90
    )


def institution_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"), index=True)


def user_fk(nullable: bool = True, **kwargs: Any) -> Mapped[Any]:
    return mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=nullable, **kwargs)
