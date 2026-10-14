"""Facebook watch-list collection end to end, through the service and the API.

Proves rule 4 (no handle, name, phone, e-mail or profile link is stored),
rule 6 (route and run on every item) and rule 9 (failures are visible).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from pnsi.collection import service as collection
from pnsi.connectors.facebook_apify import FacebookPagesApify
from pnsi.enums import CollectionRoute, Role, RunStatus, RunTrigger
from pnsi.models import AuditEvent, CollectionRun, ContentItem, Source
from pnsi.settings import Settings
from tests.apify_fake import FakeApify
from tests.integration.conftest import csrf_headers, login

# Every identifier planted in the synthetic fixtures.
PLANTED = [
    "Exemplia",
    "Testova",
    "exemplia.testova.000",
    "سلمى",
    "الاختبار",
    "98 765 432",
    "exemplia@mail.example",
    "dr_exemple_test",
    "100099999999992",
    "100099999999991",
]


@pytest.fixture
def page(db, seeded) -> Source:
    from pnsi.models import Institution

    institution = db.scalar(select(Institution).where(Institution.code == "ONMNE"))
    source = Source(
        institution_id=institution.id,
        key="facebook:pagetestpnsi",
        name="Page Test PNSI",
        kind="scraper",
        route=CollectionRoute.PUBLIC_CONTESTED,
        basis=FacebookPagesApify.basis,
        enabled=True,
        schedule="every:12h",
        config={
            "connector": FacebookPagesApify.key,
            "page_url": "https://www.facebook.com/pagetestpnsi",
            "health_filter": True,
        },
    )
    db.add(source)
    db.commit()
    return source


def run_with(db, source: Source, fake: FakeApify | None, token: str | None = "fake"):
    settings = Settings(apify_token=token, apify_max_spend_usd=5)

    def factory(_source, s):
        if fake is None:
            return FacebookPagesApify(s)
        return FacebookPagesApify(s, client_factory=fake.client)

    run = collection.create_run(db, source, RunTrigger.MANUAL)
    db.commit()
    return collection.execute_run(db, run.id, settings=settings, connector_factory=factory)


def all_stored_text(db) -> str:
    """Every text column of every table a collection writes to."""
    parts = []
    for table in ("content_items", "content_item_revisions", "collection_runs", "sources"):
        rows = db.execute(text(f"SELECT row_to_json(t)::text FROM {table} t")).scalars()  # noqa: S608
        parts.extend(rows)
    return "\n".join(parts)


def test_no_personal_identifier_is_stored(db, page):
    run = run_with(db, page, FakeApify())
    assert run.status is RunStatus.PARTIAL  # the fixture's error row is reported
    stored = all_stored_text(db)
    for value in PLANTED:
        assert value not in stored, f"{value!r} reached the database"
    comments = db.scalars(select(ContentItem).where(ContentItem.parent_id.is_not(None))).all()
    texts = " ".join(c.original_text for c in comments)
    for placeholder in ("[nom]", "[téléphone]", "[e-mail]", "[pseudo]", "[lien de profil]"):
        assert placeholder in texts
    # Meaning is kept: the Derja negation and the Arabizi words survive untouched.
    assert "ما يسببش" in texts and "ma3andich thi9a" in texts


def test_items_record_route_source_and_run(db, page):
    run = run_with(db, page, FakeApify())
    items = db.scalars(select(ContentItem)).all()
    assert len(items) == 5  # 2 health posts + 3 comments
    for item in items:
        assert item.route is CollectionRoute.PUBLIC_CONTESTED
        assert item.source_id == page.id and item.run_id == run.id
        assert item.is_scenario is False
        assert item.redaction_version
    individual = [i for i in items if i.author_kind.value == "individual"]
    assert individual and all(
        i.canonical_url is None and i.author_org_name is None for i in individual
    )
    assert run.items_new == 5 and run.coverage["posts_filtered_out"] == 1


def test_second_identical_run_adds_nothing(db, page):
    run_with(db, page, FakeApify())
    second = run_with(db, page, FakeApify())
    assert db.scalar(select(text("count(*)")).select_from(ContentItem)) == 5
    assert second.items_new == 0 and second.items_duplicate == 5
    # The cursor moved on to the newest post seen.
    assert second.cursor_before == {"newest_post_at": "2026-10-12T15:45:00+00:00"}


def test_edited_text_becomes_a_revision(db, page):
    run_with(db, page, FakeApify())
    fake = FakeApify()
    fake.posts[0] = {**fake.posts[0], "text": fake.posts[0]["text"] + " (modifié)"}
    second = run_with(db, page, fake)
    assert second.coverage["revised"] == 1
    count = db.execute(text("SELECT count(*) FROM content_item_revisions")).scalar_one()
    assert count == 1


def test_missing_token_fails_visibly_and_stores_nothing(db, page):
    run = run_with(db, page, None, token=None)
    assert run.status is RunStatus.FAILED
    assert "non configuré" in run.error
    db.refresh(page)
    assert page.last_error == run.error
    assert db.scalars(select(ContentItem)).all() == []


def test_budget_exhausted_fails_visibly(db, page):
    run = run_with(db, page, FakeApify(used_usd=5.0))
    assert run.status is RunStatus.FAILED
    assert "Budget Apify" in run.error


# API


def test_admin_adds_page_and_analyst_cannot(seeded, make_client, db):
    admin = make_client()
    login(admin, Role.ADMINISTRATEUR, seeded["administrateur"])
    body = {
        "url": "https://m.facebook.com/pagetestpnsi/",
        "name": "Page Test PNSI",
        "health_filter": False,
        "checked_note": "Vérifiée le 13/10/2026 : publique, active, tunisienne.",
    }
    res = admin.post("/api/v1/sources/facebook-pages", json=body, headers=csrf_headers(admin))
    assert res.status_code == 201, res.text
    out = res.json()
    assert out["page_url"] == "https://www.facebook.com/pagetestpnsi"
    assert out["route"] == "public_contested"
    assert out["integration_state"] in ("configure", "non_configure")
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "source.created"))

    again = admin.post("/api/v1/sources/facebook-pages", json=body, headers=csrf_headers(admin))
    assert again.status_code == 409

    analyst = make_client()
    login(analyst, Role.ANALYSTE, seeded["analyste"])
    res = analyst.post("/api/v1/sources/facebook-pages", json=body, headers=csrf_headers(analyst))
    assert res.status_code == 403
    assert analyst.get("/api/v1/sources").status_code == 200


def test_run_request_is_queued_and_audited(seeded, make_client, db, page, monkeypatch):
    sent = []
    monkeypatch.setattr("pnsi.api.v1.sources.enqueue_run", lambda run_id: sent.append(run_id))
    admin = make_client()
    login(admin, Role.ADMINISTRATEUR, seeded["administrateur"])
    url = f"/api/v1/sources/{page.id}/runs"
    res = admin.post(url, headers=csrf_headers(admin))
    assert res.status_code == 202, res.text
    assert res.json()["status"] == "queued" and len(sent) == 1
    # A second request while the first is queued is refused.
    assert admin.post(url, headers=csrf_headers(admin)).status_code == 409
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "collection.run_requested"))
    runs = admin.get(url).json()
    assert len(runs) == 1


def test_analyst_reads_inbox_with_replies(seeded, make_client, db, page):
    run_with(db, page, FakeApify())
    analyst = make_client()
    login(analyst, Role.ANALYSTE, seeded["analyste"])
    page_res = analyst.get("/api/v1/items").json()
    assert len(page_res["items"]) == 2
    vaccination = next(i for i in page_res["items"] if i["reply_count"] == 3)
    assert vaccination["route"] == "public_contested"
    assert vaccination["source"]["name"] == "Page Test PNSI"
    detail = analyst.get(f"/api/v1/items/{vaccination['id']}").json()
    assert len(detail["replies"]) == 3
    assert all("Exemplia" not in r["original_text"] for r in detail["replies"])

    cabinet = make_client()
    login(cabinet, Role.CABINET, seeded["cabinet"])
    assert cabinet.get("/api/v1/items").status_code == 403


def test_run_of_unknown_source_is_404(seeded, make_client):
    admin = make_client()
    login(admin, Role.ADMINISTRATEUR, seeded["administrateur"])
    res = admin.post(
        "/api/v1/sources/00000000-0000-0000-0000-000000000000/runs", headers=csrf_headers(admin)
    )
    assert res.status_code == 404


def test_collection_run_rows_have_no_raw_payload(db, page):
    run_with(db, page, FakeApify())
    run = db.scalar(select(CollectionRun))
    assert "Exemplia" not in str(run.coverage) and "Exemplia" not in str(run.error)
