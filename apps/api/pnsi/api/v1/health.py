"""Health endpoints. The only routes that do not require a session (spec §15)."""

from __future__ import annotations

from typing import Literal

import redis
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from pnsi.db import get_engine
from pnsi.log import get_logger
from pnsi.settings import get_settings

router = APIRouter(prefix="/health", tags=["health"])
log = get_logger(__name__)

CheckState = Literal["ok", "en_echec"]


class LiveOut(BaseModel):
    status: Literal["ok"] = "ok"


class HealthOut(BaseModel):
    status: Literal["ok", "degrade"]
    database: CheckState
    redis: CheckState


def check_database() -> CheckState:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        log.warning("health_database_failed", error_type=type(exc).__name__)
        return "en_echec"


def check_redis() -> CheckState:
    try:
        client = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        client.ping()
        return "ok"
    except Exception as exc:
        log.warning("health_redis_failed", error_type=type(exc).__name__)
        return "en_echec"


@router.get("/live", response_model=LiveOut, operation_id="health_live")
def live() -> LiveOut:
    return LiveOut()


@router.get("", response_model=HealthOut, operation_id="health")
def health(response: Response) -> HealthOut:
    database = check_database()
    cache = check_redis()
    ok = database == "ok" and cache == "ok"
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(status="ok" if ok else "degrade", database=database, redis=cache)
