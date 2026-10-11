"""Scoped membership management (administrateur)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from pnsi.api.v1.schemas import MemberCreate, MemberOut
from pnsi.auth.deps import require
from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission
from pnsi.db import DbSession
from pnsi.errors import ERROR_RESPONSES
from pnsi.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"], responses=ERROR_RESPONSES)
UserManager = Annotated[Principal, Depends(require(Permission.USERS_MANAGE))]


@router.get("", response_model=list[MemberOut], operation_id="list_users")
def list_users(principal: UserManager, db: DbSession) -> list[MemberOut]:
    return [MemberOut.build(m) for m in user_service.list_members(db, principal)]


@router.post(
    "", response_model=MemberOut, status_code=status.HTTP_201_CREATED, operation_id="create_user"
)
def create_user(body: MemberCreate, principal: UserManager, db: DbSession) -> MemberOut:
    membership = user_service.create_member(
        db,
        principal,
        email=body.email,
        display_name=body.display_name,
        password=body.password,
        roles=set(body.roles),
        locale=body.locale,
        justification=body.justification,
    )
    db.refresh(membership.user)
    return MemberOut.build(membership)


@router.get("/{user_id}", response_model=MemberOut, operation_id="get_user")
def get_user(user_id: uuid.UUID, principal: UserManager, db: DbSession) -> MemberOut:
    return MemberOut.build(user_service.get_member(db, principal, user_id))
