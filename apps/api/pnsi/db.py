"""Database engine and per-request session.

A request gets one session; it commits when the endpoint returns and rolls
back on any error, so a domain change and its audit event are stored together
or not at all.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from pnsi.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# `scope="function"` commits before the response is sent, so a failed commit
# reaches the client as an error instead of being lost after a 200.
DbSession = Annotated[Session, Depends(get_db, scope="function")]
