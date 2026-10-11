"""Read access to the audit trail of the caller's institution."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from pnsi.api.v1.schemas import AuditEventOut, AuditPage
from pnsi.auth.deps import require
from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission
from pnsi.db import DbSession
from pnsi.errors import ERROR_RESPONSES
from pnsi.models import AuditEvent

router = APIRouter(prefix="/audit-events", tags=["audit"], responses=ERROR_RESPONSES)
AuditReader = Annotated[Principal, Depends(require(Permission.AUDIT_READ))]


@router.get("", response_model=AuditPage, operation_id="list_audit_events")
def list_audit_events(
    principal: AuditReader,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[int | None, Query(description="Return events older than this id")] = None,
    action: Annotated[str | None, Query(max_length=100)] = None,
) -> AuditPage:
    query = select(AuditEvent).where(AuditEvent.institution_id == principal.institution_id)
    if cursor is not None:
        query = query.where(AuditEvent.id < cursor)
    if action:
        query = query.where(AuditEvent.action == action)
    rows = db.scalars(query.order_by(AuditEvent.id.desc()).limit(limit + 1)).all()
    items = [AuditEventOut.model_validate(r) for r in rows[:limit]]
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    return AuditPage(items=items, next_cursor=next_cursor)
