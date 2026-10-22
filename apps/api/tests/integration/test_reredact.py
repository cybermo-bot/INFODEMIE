"""Re-redaction after a redaction fix: texts, revisions and one audit event."""

from __future__ import annotations

from sqlalchemy import select

from pnsi.cli.reredact import reredact
from pnsi.models import AuditEvent, ContentItem, ContentItemRevision
from pnsi.privacy.redact import REDACTION_VERSION
from tests.apify_fake import FakeApify
from tests.integration.test_collection import page, run_with  # noqa: F401


def test_old_versions_are_reredacted_and_audited(db, page):  # noqa: F811
    run_with(db, page, FakeApify())
    item = db.scalars(select(ContentItem)).first()
    item.original_text += " contact مرحبا@vieux_pseudo"
    item.redaction_version = "r0-test"
    db.add(
        ContentItemRevision(
            content_item_id=item.id,
            revision=1,
            run_id=item.run_id,
            original_text="ancien texte, tel 98765432",
            content_hash="x",
            metrics={},
            collected_at=item.collected_at,
        )
    )
    db.commit()

    result = reredact(db)
    assert result == {"items_checked": 1, "items_changed": 1, "revisions_changed": 1}
    db.refresh(item)
    assert "vieux_pseudo" not in item.original_text
    assert item.redaction_version == REDACTION_VERSION
    rev = db.scalars(select(ContentItemRevision)).one()
    assert "98765432" not in rev.original_text
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "privacy.reredacted")).one()
    assert event.context["from_versions"] == {"r0-test": 1}
    assert reredact(db)["items_checked"] == 0
