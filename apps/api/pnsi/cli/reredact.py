"""Re-apply the current redaction to stored texts, items and their revisions.

Run after `REDACTION_VERSION` changes because a leak was fixed. Only ever
removes more: it cannot bring back text that an earlier version removed. Each
run writes one audit event with the counts per previous version, never text.

Usage: uv run python -m pnsi.cli.reredact
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from pnsi.audit import service as audit
from pnsi.collection.service import sha256
from pnsi.db import get_sessionmaker
from pnsi.models import ContentItem, ContentItemRevision
from pnsi.privacy.redact import REDACTION_VERSION, redact


def reredact(db: Session) -> dict[str, int]:
    seen: Counter[str] = Counter()
    changed = 0
    items = db.scalars(
        select(ContentItem).where(ContentItem.redaction_version != REDACTION_VERSION)
    ).all()
    for item in items:
        seen[item.redaction_version] += 1
        text = redact(item.original_text).text
        if text != item.original_text:
            item.original_text = text
            item.content_hash = sha256(text)
            changed += 1
        item.redaction_version = REDACTION_VERSION
    revisions_changed = 0
    item_ids = [i.id for i in items]
    if item_ids:
        for rev in db.scalars(
            select(ContentItemRevision).where(ContentItemRevision.content_item_id.in_(item_ids))
        ):
            text = redact(rev.original_text).text
            if text != rev.original_text:
                rev.original_text = text
                rev.content_hash = sha256(text)
                revisions_changed += 1
    result = {
        "items_checked": len(items),
        "items_changed": changed,
        "revisions_changed": revisions_changed,
    }
    if items:
        audit.record(
            db,
            "privacy.reredacted",
            object_type="content_items",
            context={**result, "to_version": REDACTION_VERSION, "from_versions": dict(seen)},
        )
    db.commit()
    return result


def main() -> None:
    with get_sessionmaker()() as db:
        result = reredact(db)
    print(
        f"Version {REDACTION_VERSION} : {result['items_checked']} élément(s) vérifié(s), "
        f"{result['items_changed']} modifié(s), "
        f"{result['revisions_changed']} révision(s) modifiée(s)."
    )


if __name__ == "__main__":
    main()
