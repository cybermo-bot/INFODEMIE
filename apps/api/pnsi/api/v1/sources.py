"""Source registry, the Facebook watch-list and collection runs."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from pnsi.api.v1.collection_schemas import (
    FacebookPageCreate,
    RunOut,
    SourceOut,
    SourcePatch,
)
from pnsi.auth.deps import SettingsDep, require
from pnsi.auth.principal import Principal
from pnsi.authz.permissions import Permission
from pnsi.collection.dispatch import enqueue_run
from pnsi.db import DbSession
from pnsi.errors import ERROR_RESPONSES
from pnsi.services import sources as source_service

router = APIRouter(tags=["sources"], responses=ERROR_RESPONSES)
SourceReader = Annotated[Principal, Depends(require(Permission.SOURCES_READ))]
SourceManager = Annotated[Principal, Depends(require(Permission.SOURCES_MANAGE))]


def _out(db, source, settings) -> SourceOut:
    last = source_service.latest_runs(db, [source.id]).get(source.id)
    return SourceOut.build(source, last, settings.integration_status())


@router.get("/sources", response_model=list[SourceOut], operation_id="list_sources")
def list_sources(principal: SourceReader, db: DbSession, settings: SettingsDep) -> list[SourceOut]:
    sources = source_service.list_sources(db, principal)
    runs = source_service.latest_runs(db, [s.id for s in sources])
    integrations = settings.integration_status()
    return [SourceOut.build(s, runs.get(s.id), integrations) for s in sources]


@router.post(
    "/sources/facebook-pages",
    response_model=SourceOut,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_facebook_page",
)
def add_facebook_page(
    body: FacebookPageCreate, principal: SourceManager, db: DbSession, settings: SettingsDep
) -> SourceOut:
    source = source_service.add_facebook_page(
        db,
        principal,
        url=body.url,
        name=body.name,
        health_filter=body.health_filter,
        checked_note=body.checked_note,
        posts_per_run=body.posts_per_run,
        comments_per_post=body.comments_per_post,
    )
    return _out(db, source, settings)


@router.patch("/sources/{source_id}", response_model=SourceOut, operation_id="update_source")
def update_source(
    source_id: uuid.UUID,
    body: SourcePatch,
    principal: SourceManager,
    db: DbSession,
    settings: SettingsDep,
) -> SourceOut:
    source = source_service.update_source(
        db,
        principal,
        source_id,
        expected_version=body.expected_version,
        enabled=body.enabled,
        health_filter=body.health_filter,
        posts_per_run=body.posts_per_run,
        comments_per_post=body.comments_per_post,
    )
    return _out(db, source, settings)


@router.post(
    "/sources/{source_id}/runs",
    response_model=RunOut,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="request_collection_run",
)
def request_run(
    source_id: uuid.UUID, principal: SourceManager, db: DbSession, background: BackgroundTasks
) -> RunOut:
    run = source_service.request_run(db, principal, source_id)
    # Runs after the response, so after the commit: the worker always finds the run.
    background.add_task(enqueue_run, run.id)
    return RunOut.model_validate(run)


@router.get(
    "/sources/{source_id}/runs", response_model=list[RunOut], operation_id="list_collection_runs"
)
def list_runs(
    source_id: uuid.UUID,
    principal: SourceReader,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[RunOut]:
    return [
        RunOut.model_validate(r) for r in source_service.list_runs(db, principal, source_id, limit)
    ]


@router.get("/runs/{run_id}", response_model=RunOut, operation_id="get_collection_run")
def get_run(run_id: uuid.UUID, principal: SourceReader, db: DbSession) -> RunOut:
    return RunOut.model_validate(source_service.get_run(db, principal, run_id))
