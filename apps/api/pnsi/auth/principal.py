"""The authenticated caller, as seen by services and authorisation checks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from pnsi.authz.permissions import Permission, permissions_for
from pnsi.enums import Role


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    institution_id: uuid.UUID
    roles: frozenset[Role]
    session_id: uuid.UUID | None = None
    permissions: frozenset[Permission] = field(default=frozenset())

    @classmethod
    def build(
        cls,
        user_id: uuid.UUID,
        institution_id: uuid.UUID,
        roles: frozenset[Role],
        session_id: uuid.UUID | None = None,
    ) -> Principal:
        return cls(user_id, institution_id, roles, session_id, permissions_for(roles))

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions
