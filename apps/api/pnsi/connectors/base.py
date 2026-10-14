"""Connector contract.

A connector fetches from one source and returns raw text with the names it
knows belong to individuals. It never stores anything: the collection service
redacts every text before it reaches the database, so no connector can forget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pnsi.enums import AuthorKind, CollectionRoute
from pnsi.models import Source
from pnsi.settings import Settings


class ConfigStatus(StrEnum):
    OK = "ok"
    NOT_CONFIGURED = "non_configure"
    INVALID = "invalide"


class ConnectorError(Exception):
    """A readable failure, safe to show in the interface (no secret, no personal data)."""


class NotConfigured(ConnectorError):
    pass


class BudgetExhausted(ConnectorError):
    pass


@dataclass
class ItemIn:
    external_id: str
    # Raw text as fetched. Lives in memory only; the service stores the redacted form.
    raw_text: str
    published_at: datetime | None = None
    parent_external_id: str | None = None
    # Kept only for organisation and media pages.
    canonical_url: str | None = None
    author_kind: AuthorKind = AuthorKind.UNKNOWN
    author_org_name: str | None = None
    # Names of individuals seen in this thread, removed from the text.
    known_names: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Batch:
    items: list[ItemIn] = field(default_factory=list)
    cursor_after: dict[str, Any] | None = None
    # What was covered: queries, pages, time window, filtered counts, cost.
    coverage: dict[str, Any] = field(default_factory=dict)
    # Readable errors for parts that failed while the rest succeeded.
    partial_errors: list[str] = field(default_factory=list)


class Connector(Protocol):
    key: str
    route: CollectionRoute
    basis: str

    def validate_config(self, settings: Settings) -> ConfigStatus: ...

    def fetch(self, source: Source, cursor: dict[str, Any] | None) -> Batch: ...
