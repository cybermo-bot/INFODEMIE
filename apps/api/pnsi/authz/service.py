"""Central authorisation service. Every domain service calls `ensure_can`.

Checks run before any count, file access or existence leak (spec §15). An
object from another institution answers 404, so its existence is not revealed.
"""

from __future__ import annotations

import uuid
from typing import Any

from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission
from pnsi.errors import Forbidden, NotFound


def ensure_permission(principal: Principal, permission: Permission) -> None:
    if not principal.has(permission):
        raise Forbidden(code="forbidden", message="Action non autorisée pour ce rôle.")


def ensure_in_scope(principal: Principal, obj: Any | None) -> None:
    """The object must belong to the caller's institution."""
    if obj is None:
        raise NotFound()
    institution_id: uuid.UUID | None = getattr(obj, "institution_id", None)
    if institution_id is None or institution_id != principal.institution_id:
        raise NotFound()


def ensure_can(principal: Principal, permission: Permission, obj: Any | None = None) -> None:
    ensure_permission(principal, permission)
    if obj is not None:
        ensure_in_scope(principal, obj)
