"""Append-only audit trail, written by domain services in the same transaction as the change."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from pnsi.errors import request_id_var
from pnsi.log import MASK, SENSITIVE_KEY
from pnsi.models import AuditEvent

if TYPE_CHECKING:
    from pnsi.auth.principal import Principal


def _clean(value: Any, key: str | None = None) -> Any:
    if key is not None and (SENSITIVE_KEY.search(key) or key.endswith("_hash")):
        return MASK
    if isinstance(value, Mapping):
        return {str(k): _clean(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_clean(v) for v in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value") and isinstance(value.value, str):  # enums
        return value.value
    return value


def diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """{field: {"from": old, "to": new}} for the fields that changed."""
    return {
        k: {"from": before.get(k), "to": after.get(k)}
        for k in sorted(set(before) | set(after))
        if before.get(k) != after.get(k)
    }


def record(
    db: Session,
    action: str,
    *,
    actor: Principal | None = None,
    actor_id: uuid.UUID | None = None,
    institution_id: uuid.UUID | None = None,
    object_type: str | None = None,
    object_id: uuid.UUID | str | None = None,
    changes: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        actor_id=actor.user_id if actor else actor_id,
        actor_roles=sorted(r.value for r in actor.roles) if actor else [],
        institution_id=institution_id or (actor.institution_id if actor else None),
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        changes=_clean(dict(changes or {})),
        context=_clean(dict(context or {})),
        request_id=request_id_var.get(),
    )
    db.add(event)
    return event
