"""Facebook Pages and public groups through Apify: parsing, filter, budget guard. No network."""

from __future__ import annotations

import pytest

from pnsi.connectors.apify import ApifyClient, Budget, run_cost_usd
from pnsi.connectors.base import BudgetExhausted, ConfigStatus, NotConfigured
from pnsi.connectors.facebook_apify import (
    COMMENTS_ACTOR,
    GROUPS_ACTOR,
    POSTS_ACTOR,
    FacebookGroupsApify,
    FacebookPagesApify,
    normalize_group_url,
    normalize_page_url,
)
from pnsi.enums import AuthorKind, SourceKind
from pnsi.models import Source
from pnsi.settings import Settings
from tests.apify_fake import FakeApify


def make_source(**config) -> Source:
    return Source(
        key="facebook:pagetestpnsi",
        name="Page Test PNSI",
        kind=SourceKind.SCRAPER,
        route=FacebookPagesApify.route,
        basis=FacebookPagesApify.basis,
        config={
            "connector": FacebookPagesApify.key,
            "page_url": "https://www.facebook.com/pagetestpnsi",
            **config,
        },
    )


def connector(fake: FakeApify, max_spend: float = 5.0) -> FacebookPagesApify:
    settings = Settings(apify_token="fake", apify_max_spend_usd=max_spend)
    return FacebookPagesApify(settings, client_factory=fake.client)


def test_not_configured_without_token():
    settings = Settings(apify_token=None)
    assert FacebookPagesApify(settings).validate_config(settings) is ConfigStatus.NOT_CONFIGURED
    with pytest.raises(NotConfigured):
        ApifyClient(None)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("facebook.com/pagetestpnsi/", "https://www.facebook.com/pagetestpnsi"),
        ("https://m.facebook.com/pagetestpnsi", "https://www.facebook.com/pagetestpnsi"),
        (
            "https://www.facebook.com/profile.php?id=61500000000000",
            "https://www.facebook.com/profile.php?id=61500000000000",
        ),
    ],
)
def test_page_url_normalised(url, expected):
    assert normalize_page_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://www.facebook.com/groups/123",
        "https://example.com/page",
        "https://www.facebook.com/",
    ],
)
def test_non_page_urls_rejected(url):
    with pytest.raises(ValueError):
        normalize_page_url(url)


def test_health_filter_keeps_health_posts_and_their_comments():
    fake = FakeApify()
    batch = connector(fake).fetch(make_source(), None)

    posts = [i for i in batch.items if i.parent_external_id is None]
    comments = [i for i in batch.items if i.parent_external_id is not None]
    # Vaccination post and the Arabic medicines link post pass; the football post does not.
    assert {p.external_id for p in posts} == {
        "facebook:post:900000000000001",
        "facebook:post:900000000000003",
    }
    assert batch.coverage["posts_filtered_out"] == 1
    assert all(p.author_kind is AuthorKind.ORGANISATION for p in posts)
    assert all(p.author_org_name == "Page Test PNSI" for p in posts)
    # Comments only for the relevant post that has comments; the one without id is skipped.
    assert [r["actor"] for r in fake.runs] == [POSTS_ACTOR, COMMENTS_ACTOR]
    assert len(comments) == 3
    # The Page answering in its own comments is an organisation, people are individuals.
    kinds = {c.external_id: c.author_kind for c in comments}
    assert kinds["facebook:comment:700000000000003"] is AuthorKind.ORGANISATION
    assert kinds["facebook:comment:700000000000001"] is AuthorKind.INDIVIDUAL
    # Commenter names are handed over for redaction, the Page name is not.
    names = comments[0].known_names
    assert "Exemplia Testova" in names and "سلمى الاختبار" in names
    assert "Page Test PNSI" not in names
    # The error row is reported, not hidden.
    assert batch.partial_errors
    assert batch.cursor_after == {"newest_post_at": "2026-10-12T15:45:00+00:00"}


def test_cursor_is_used_on_next_run():
    fake = FakeApify()
    connector(fake).fetch(make_source(), {"newest_post_at": "2026-10-12T15:45:00+00:00"})
    assert fake.runs[0]["input"]["onlyPostsNewerThan"] == "2026-10-12T15:45:00+00:00"


def test_without_filter_every_post_is_kept():
    fake = FakeApify()
    batch = connector(fake).fetch(make_source(health_filter=False), None)
    assert len([i for i in batch.items if i.parent_external_id is None]) == 3


def test_every_run_is_capped_below_the_remaining_budget():
    fake = FakeApify(used_usd=4.9)
    connector(fake, max_spend=5.0).fetch(make_source(), None)
    posts_run, *comment_runs = fake.runs
    assert comment_runs
    # Each cap fits what is left once earlier runs are charged at their real cost.
    assert posts_run["max_charge"] <= 0.1 + 1e-9
    assert fake.post_run_cost + sum(r["max_charge"] for r in comment_runs) <= 0.1 + 1e-9


def test_budget_exhausted_stops_before_any_run():
    fake = FakeApify(used_usd=4.995)
    with pytest.raises(BudgetExhausted):
        connector(fake, max_spend=5.0).fetch(make_source(), None)
    assert fake.runs == []


def test_account_limit_lower_than_ours_wins():
    fake = FakeApify(used_usd=1.0, account_max_usd=1.0)
    with pytest.raises(BudgetExhausted):
        connector(fake, max_spend=5.0).fetch(make_source(), None)


def test_comments_stop_when_budget_runs_out_mid_way():
    # Enough for the posts run but not for a comments run: posts kept, error reported.
    fake = FakeApify(used_usd=4.95, post_run_cost=0.03)
    batch = connector(fake, max_spend=5.0).fetch(make_source(), None)
    assert [r["actor"] for r in fake.runs] == [POSTS_ACTOR]
    assert any("Budget Apify" in e for e in batch.partial_errors)
    assert all(i.parent_external_id is None for i in batch.items)


def test_rejected_token_is_not_configured():
    fake = FakeApify(status_code=401)
    with pytest.raises(NotConfigured):
        connector(fake).fetch(make_source(), None)


def test_budget_cap_arithmetic():
    budget = Budget(remaining_usd=0.5)
    assert budget.cap(0.2) == 0.2
    budget.charge(0.45)
    assert budget.cap(0.2) == 0.05
    budget.charge(0.04)
    with pytest.raises(BudgetExhausted):
        budget.cap(0.2)


def test_unreported_cost_is_charged_from_items_received():
    # Apify said 0 USD; three posts at 0.007 plus the start must still count.
    fake = FakeApify(report_cost=False)
    batch = connector(fake).fetch(make_source(comments_per_post=0), None)
    assert batch.coverage["cost_usd"] == pytest.approx(0.001 + 3 * 0.007)


def test_run_cost_reads_charged_events_when_usage_is_late():
    run = {
        "usageTotalUsd": 0.0,
        "chargedEventCounts": {"post": 7, "actor-start": 1, "filter-applied": 7},
        "pricingInfo": {
            "pricingPerEvent": {
                "actorChargeEvents": {
                    "post": {"eventPriceUsd": 0.005},
                    "actor-start": {"eventPriceUsd": 0.001},
                    "filter-applied": {"eventPriceUsd": 0.002},
                }
            }
        },
    }
    assert run_cost_usd(run) == pytest.approx(0.05)
    assert run_cost_usd({"usageTotalUsd": 0.2}) == 0.2


def test_empty_window_is_coverage_not_an_error():
    fake = FakeApify(posts=[{"error": "no_items", "errorDescription": "Empty or private data"}])
    batch = connector(fake).fetch(make_source(), None)
    assert batch.items == []
    assert batch.partial_errors == []
    assert batch.coverage["no_items"] is True


# Public groups (decision D18)


def make_group(**config) -> Source:
    return Source(
        key="facebook:groups-groupetestpnsi",
        name="Groupe Test PNSI",
        kind=SourceKind.SCRAPER,
        route=FacebookGroupsApify.route,
        basis=FacebookGroupsApify.basis,
        config={
            "connector": FacebookGroupsApify.key,
            "group_url": "https://www.facebook.com/groups/groupetestpnsi",
            **config,
        },
    )


def group_connector(fake: FakeApify) -> FacebookGroupsApify:
    settings = Settings(apify_token="fake", apify_max_spend_usd=5.0)
    return FacebookGroupsApify(settings, client_factory=fake.client)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://www.facebook.com/groups/a5bar.tounes?locale=fr_FR",
            "https://www.facebook.com/groups/a5bar.tounes",
        ),
        (
            "m.facebook.com/groups/121472527925795/",
            "https://www.facebook.com/groups/121472527925795",
        ),
    ],
)
def test_group_url_normalised(url, expected):
    assert normalize_group_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://www.facebook.com/mosaiquefm",
        "https://www.facebook.com/groups/",
        "https://www.facebook.com/groups/123/permalink/456",
    ],
)
def test_non_group_urls_rejected(url):
    with pytest.raises(ValueError):
        normalize_group_url(url)


def test_group_posts_are_individuals_with_names_handed_to_redaction():
    fake = FakeApify()
    batch = group_connector(fake).fetch(make_group(), None)

    assert [r["actor"] for r in fake.runs] == [GROUPS_ACTOR]
    assert fake.runs[0]["input"]["viewOption"] == "CHRONOLOGICAL"
    by_id = {i.external_id: i for i in batch.items}
    # The car sale is filtered out; the vaccine question and the shared rumour stay.
    assert set(by_id) == {
        "facebook:group-post:800000000000001",
        "facebook:group-post:800000000000003",
    }
    assert batch.coverage["posts_filtered_out"] == 1
    for item in batch.items:
        assert item.author_kind is AuthorKind.INDIVIDUAL
        assert item.author_org_name is None
        # No link back to a post written by a private person.
        assert item.canonical_url is None
    first = by_id["facebook:group-post:800000000000001"]
    assert "Exemplia Testova" in first.known_names
    assert first.known_full_names == ["Rym Fictive"]
    shared = by_id["facebook:group-post:800000000000003"]
    assert "grippe" in shared.raw_text
    assert "Partageur Fictif" in shared.known_names
    assert first.metrics["comments"] == 7


def test_group_comments_are_never_requested():
    # Group posts have comments, but logged-out access returns nothing for them.
    fake = FakeApify()
    group_connector(fake).fetch(make_group(comments_per_post=20), None)
    assert COMMENTS_ACTOR not in [r["actor"] for r in fake.runs]


def test_shared_page_post_keeps_the_page_name():
    post = {
        "legacyId": "1",
        "user": {"name": "Exemplia Testova"},
        "text": "",
        "sharedPost": {
            "text": "Communiqué du Ministère de la Santé publique sur la rougeole.",
            "pageName": {"name": "Ministère de la Santé publique"},
            "user": {"name": "Ministère de la Santé publique"},
        },
    }
    fake = FakeApify(group_posts=[post])
    batch = group_connector(fake).fetch(make_group(health_filter=False), None)
    assert batch.items[0].known_names == ["Exemplia Testova"]


def test_group_post_id_is_stable_across_fields():
    from pnsi.connectors.facebook_apify import _group_post_id

    full = {
        "legacyId": "800000000000001",
        "id": "UzpfSTEwMDAwMDAwMDAwMDAwMTpWSzo4MDAwMDAwMDAwMDAwMDE=",
        "url": "https://www.facebook.com/groups/g/permalink/800000000000001/",
    }
    assert _group_post_id(full) == "800000000000001"
    assert _group_post_id({k: v for k, v in full.items() if k != "legacyId"}) == "800000000000001"
    assert _group_post_id({"url": full["url"]}) == "800000000000001"
    assert _group_post_id({"id": "not-base64!"}) is None


def test_apify_copy_of_raw_items_is_deleted_after_reading():
    fake = FakeApify()
    batch = connector(fake).fetch(make_source(), None)
    # Posts run and comments run: dataset and key-value store of each.
    assert sorted(fake.deleted) == [
        "/v2/datasets/ds-0",
        "/v2/datasets/ds-1",
        "/v2/key-value-stores/kv-0",
        "/v2/key-value-stores/kv-1",
    ]
    assert batch.coverage["apify_storage_deleted"] is True
    assert "_comment_storage_deleted" not in batch.coverage


def test_failed_deletion_is_reported():
    fake = FakeApify(delete_ok=False)
    batch = connector(fake).fetch(make_source(comments_per_post=0), None)
    assert batch.coverage["apify_storage_deleted"] is False
    assert any("Copie brute" in e for e in batch.partial_errors)


def test_full_page_of_posts_is_flagged_as_possibly_truncated():
    fake = FakeApify()
    batch = connector(fake).fetch(make_source(posts_per_run=3, comments_per_post=0), None)
    assert batch.coverage["possibly_truncated"] is True
    batch = connector(FakeApify()).fetch(make_source(comments_per_post=0), None)
    assert batch.coverage["possibly_truncated"] is False


def test_ads_are_tagged_not_dropped():
    ad = {
        "legacyId": "2",
        "user": {"name": "Vendeur Fictif"},
        "text": "مكمل طبيعي يعالج السكري، متوفر الآن، السعر 45 دينار، 98765432",
    }
    news = {"legacyId": "3", "text": "Le prix des médicaments contre le diabète augmente."}
    fake = FakeApify(group_posts=[ad, news])
    batch = group_connector(fake).fetch(make_group(health_filter=False), None)
    by_id = {i.external_id: i for i in batch.items}
    tagged = by_id["facebook:group-post:2"]
    assert tagged.metrics["commercial"] is True
    assert "téléphone" in tagged.metrics["commercial_cues"]
    assert "commercial" not in by_id["facebook:group-post:3"].metrics
    assert batch.coverage["posts_commercial"] == 1


@pytest.mark.parametrize(
    "text",
    [
        "Campagne de vaccination gratuite, disponible dans les centres de santé. "
        "Numéro vert : 80 101 919",
        "اللقاح متوفر مجانا في مراكز الصحة الأساسية، الرقم الأخضر 80101919",
        "الدواء غير متوفر في الصيدليات، سعر البديل مرتفع",
        "Le prix des médicaments contre le diabète augmente.",
    ],
)
def test_health_signals_are_not_ads(text):
    from pnsi.collection.relevance import commercial_cues_in, is_commercial

    assert not is_commercial(commercial_cues_in(text))


@pytest.mark.parametrize(
    "text",
    [
        "مكمل طبيعي يعالج السكري، متوفر الآن، السعر 45 دينار",
        "Tisane contre la grippe, livraison partout, prix en inbox",
        "عسل حر للبيع، التوصيل لكل الولايات 98765432",
    ],
)
def test_selling_posts_are_ads(text):
    from pnsi.collection.relevance import commercial_cues_in, is_commercial

    assert is_commercial(commercial_cues_in(text))


def test_verified_tag_keeps_its_name():
    post = {
        "legacyId": "5",
        "user": {"name": "Exemplia Testova"},
        "text": "Merci au Ministère de la Santé publique pour la campagne de vaccination.",
        "textReferences": [
            {"short_name": "Ministère de la Santé publique", "is_verified": True},
            {"short_name": "Rym Fictive", "is_verified": False},
        ],
    }
    batch = group_connector(FakeApify(group_posts=[post])).fetch(make_group(), None)
    assert batch.items[0].known_full_names == ["Rym Fictive"]
