"""The committed watch-list loads, is idempotent and schedules nothing on its own."""

from __future__ import annotations

from sqlalchemy import func, select

from pnsi.cli.watchlist import load
from pnsi.models import Source


def test_watchlist_loads_once_and_stays_manual(db, seeded):
    first = load(db)
    assert first and all(status == "ajoutée" for status, _ in first)
    sources = db.scalars(select(Source)).all()
    assert len(sources) == len(first)
    assert all(s.schedule == "manual" for s in sources)
    groups = [s for s in sources if s.config["connector"] == "facebook_groups_apify"]
    assert groups and all(g.config["comments_per_post"] == 0 for g in groups)

    second = load(db)
    assert all(status == "déjà présente" for status, _ in second)
    assert db.scalar(select(func.count()).select_from(Source)) == len(first)
