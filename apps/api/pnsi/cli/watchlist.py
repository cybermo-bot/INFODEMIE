"""Load the Facebook watch-list into the database and run collections by hand.

The list lives in docs/sources/facebook-watchlist.yaml. Loading adds the Pages
and groups that are missing, as the seeded administrator, and never changes or
removes an existing source. Collecting runs each enabled Facebook source now,
one after the other, and prints counts, cost and errors only (no collected text).

Usage:
  uv run python -m pnsi.cli.watchlist load
  uv run python -m pnsi.cli.watchlist collect [--only TEXT]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from pnsi.auth.principal import Principal
from pnsi.cli.seed import INSTITUTION, seed_email
from pnsi.collection import service as collection
from pnsi.connectors.facebook_apify import FacebookGroupsApify, FacebookPagesApify
from pnsi.db import get_sessionmaker
from pnsi.enums import Role, RunTrigger
from pnsi.errors import Conflict
from pnsi.models import Institution, Source, User
from pnsi.services import sources as source_service
from pnsi.settings import REPO_ROOT

WATCHLIST = REPO_ROOT / "docs" / "sources" / "facebook-watchlist.yaml"
FACEBOOK_CONNECTORS = {FacebookPagesApify.key, FacebookGroupsApify.key}


def _admin(db: Session) -> Principal:
    institution = db.scalar(select(Institution).where(Institution.code == INSTITUTION["code"]))
    user = db.scalar(select(User).where(User.email == seed_email(Role.ADMINISTRATEUR)))
    if institution is None or user is None:
        sys.exit("Base vide : lancez d'abord `make seed`.")
    return Principal.build(user.id, institution.id, frozenset({Role.ADMINISTRATEUR}))


def load(db: Session, path: Path = WATCHLIST) -> list[tuple[str, str]]:
    """Add what is missing. Returns (status, name) for every entry."""
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    principal = _admin(db)
    schedule = data.get("schedule") or "manual"
    report: list[tuple[str, str]] = []
    entries = [("page", e) for e in data.get("pages") or []]
    entries += [("group", e) for e in data.get("groups") or []]
    for kind, entry in entries:
        add = (
            source_service.add_facebook_group
            if kind == "group"
            else (source_service.add_facebook_page)
        )
        try:
            source = add(
                db,
                principal,
                url=entry["url"],
                name=entry["name"],
                health_filter=bool(entry.get("health_filter", True)),
                checked_note=entry.get("note") or "Liste de veille de Mozart.",
            )
        except Conflict:
            db.rollback()
            report.append(("déjà présente", entry["name"]))
            continue
        source.schedule = schedule
        db.commit()
        report.append(("ajoutée", entry["name"]))
    return report


def collect(db: Session, only: str | None = None) -> list[dict[str, Any]]:
    """Run every enabled Facebook source now. Returns one summary per run."""
    collection.fail_stale_runs(db)
    sources = db.scalars(select(Source).where(Source.enabled.is_(True)).order_by(Source.name))
    summaries = []
    for source in sources:
        if (source.config or {}).get("connector") not in FACEBOOK_CONNECTORS:
            continue
        if only and only.lower() not in f"{source.name} {source.key}".lower():
            continue
        if collection.active_run(db, source) is not None:
            summaries.append({"source": source.name, "status": "déjà en cours"})
            continue
        run = collection.create_run(db, source, RunTrigger.MANUAL)
        db.commit()
        run = collection.execute_run(db, run.id)
        cov = run.coverage or {}
        summaries.append(
            {
                "source": source.name,
                "status": run.status.value,
                "posts": cov.get("posts_fetched"),
                "kept": run.items_new + run.items_duplicate,
                "new": run.items_new,
                "comments": cov.get("comments_fetched"),
                "cost_usd": cov.get("cost_usd"),
                "error": run.error,
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("load", help="ajouter les sources manquantes de la liste de veille")
    run = sub.add_parser("collect", help="collecter maintenant chaque source Facebook active")
    run.add_argument("--only", help="seulement les sources dont le nom ou la clé contient ce texte")
    args = parser.parse_args()

    with get_sessionmaker()() as db:
        if args.command == "load":
            for status, name in load(db):
                print(f"{status:14} {name}")
            return
        total = 0.0
        for s in collect(db, args.only):
            total += s.get("cost_usd") or 0
            line = f"{s['status']:10} {s['source']}"
            if "posts" in s:
                line += (
                    f" | publications {s['posts'] or 0}, gardées {s['kept']}"
                    f" (nouvelles {s['new']}),"
                    f" commentaires {s['comments'] or 0}, coût {s['cost_usd'] or 0:.3f} USD"
                )
            if s.get("error"):
                line += f" | {s['error']}"
            print(line)
        print(f"Coût estimé de cette collecte : {total:.3f} USD")


if __name__ == "__main__":
    main()
