"""Which connector serves a source, from `source.config["connector"]`."""

from __future__ import annotations

from pnsi.connectors.base import Connector, NotConfigured
from pnsi.connectors.facebook_apify import FacebookPagesApify
from pnsi.models import Source
from pnsi.settings import Settings

CONNECTORS = {FacebookPagesApify.key: FacebookPagesApify}


def connector_for(source: Source, settings: Settings) -> Connector:
    key = (source.config or {}).get("connector")
    cls = CONNECTORS.get(key or "")
    if cls is None:
        raise NotConfigured(f"Aucun connecteur pour cette source ({key or 'non précisé'}).")
    return cls(settings)
