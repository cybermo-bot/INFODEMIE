"""Facebook public Pages through Apify actors (route `public_contested`, decision D4).

Logged-out collection of a small, hand-checked watch-list of public Pages:
the posts of each Page, then the comments of the posts that pass the health
filter. Actors and fields checked on 2026-10-13:

- `apify/facebook-posts-scraper` (build 0.0.402): input `startUrls`,
  `resultsLimit` (posts per Page), `onlyPostsNewerThan`.
- `apify/facebook-comments-scraper` (build 0.0.372): input `startUrls` (post
  URLs), `resultsLimit`, `includeNestedComments`.

Prices on the Apify free plan on that date: 0.005 USD per post, 0.0025 USD per
comment, 0.001 USD per actor start. Comments are run one post at a time so
`resultsLimit` is unambiguously a per-post limit.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from pnsi.collection.relevance import HEALTH_TERMS_VERSION, health_terms_in
from pnsi.connectors.apify import ApifyClient, Budget
from pnsi.connectors.base import (
    Batch,
    BudgetExhausted,
    ConfigStatus,
    ConnectorError,
    ItemIn,
)
from pnsi.enums import AuthorKind, CollectionRoute
from pnsi.models import Source
from pnsi.settings import Settings

POSTS_ACTOR = "apify~facebook-posts-scraper"
COMMENTS_ACTOR = "apify~facebook-comments-scraper"
PRICE_POST_USD = 0.005
PRICE_COMMENT_USD = 0.0025
PRICE_START_USD = 0.001
MARGIN = 1.2

DEFAULTS: dict[str, Any] = {
    "posts_per_run": 10,
    "comments_per_post": 20,
    "first_run_lookback": "3 days",
    "health_filter": True,
}

FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com"}


def normalize_page_url(url: str) -> str:
    """https://www.facebook.com/<page>, or ValueError when it is not a Facebook Page URL."""
    raw = url.strip()
    if "://" not in raw:
        raw = "https://" + raw
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    path = parts.path.strip("/")
    if host not in FACEBOOK_HOSTS or not path:
        raise ValueError("adresse de Page Facebook attendue (https://www.facebook.com/...)")
    if path.split("/")[0] in {"groups", "events", "watch", "share", "story.php", "photo"}:
        raise ValueError("une Page publique est attendue, pas un groupe ni une publication")
    query = f"?{parts.query}" if path == "profile.php" and parts.query else ""
    return f"https://www.facebook.com/{path}{query}"


def _same_page(url: str | None, page_url: str) -> bool:
    if not url:
        return False
    try:
        return normalize_page_url(url).lower() == page_url.lower()
    except ValueError:
        return False


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _page_name(post: dict[str, Any]) -> str | None:
    name = post.get("pageName")
    if isinstance(name, dict):
        name = name.get("name")
    if not name and isinstance(post.get("user"), dict):
        name = post["user"].get("name")
    return name or None


def _post_text(post: dict[str, Any]) -> str:
    text = post.get("text") or ""
    if text:
        return text
    # Link posts without a caption: keep the shared article's title and summary.
    return "\n".join(p for p in (post.get("previewTitle"), post.get("previewDescription")) if p)


def _commenter_names(comment: dict[str, Any]) -> list[str]:
    names = [comment.get("profileName"), comment.get("name")]
    author = comment.get("author")
    if isinstance(author, dict):
        names.append(author.get("name"))
    return [n for n in names if n]


class FacebookPagesApify:
    key = "facebook_pages_apify"
    route = CollectionRoute.PUBLIC_CONTESTED
    basis = (
        "Collecte sans connexion de Pages Facebook publiques d'une liste vérifiée, via les "
        "acteurs Apify facebook-posts-scraper et facebook-comments-scraper. Position "
        "juridique contestée par Meta (décision D4) : liste restreinte, rythme modéré."
    )

    def __init__(self, settings: Settings, client_factory=None) -> None:
        self.settings = settings
        self._client_factory = client_factory or (
            lambda: ApifyClient(
                settings.apify_token.get_secret_value() if settings.apify_token else None
            )
        )

    def validate_config(self, settings: Settings) -> ConfigStatus:
        return ConfigStatus.OK if settings.apify_token else ConfigStatus.NOT_CONFIGURED

    def fetch(self, source: Source, cursor: dict[str, Any] | None) -> Batch:
        cfg = {**DEFAULTS, **(source.config or {})}
        page_url = normalize_page_url(cfg["page_url"])
        client = self._client_factory()
        try:
            return self._fetch(client, cfg, page_url, cursor or {})
        finally:
            client.close()

    def _fetch(
        self, client: ApifyClient, cfg: dict[str, Any], page_url: str, cursor: dict[str, Any]
    ) -> Batch:
        budget = client.budget(self.settings.apify_max_spend_usd)
        posts_limit = int(cfg["posts_per_run"])
        comments_limit = int(cfg["comments_per_post"])
        newer_than = cursor.get("newest_post_at") or cfg["first_run_lookback"]

        posts_cap = budget.cap(MARGIN * (PRICE_START_USD + posts_limit * PRICE_POST_USD))
        result = client.run_actor(
            POSTS_ACTOR,
            {
                "startUrls": [{"url": page_url}],
                "resultsLimit": posts_limit,
                "onlyPostsNewerThan": newer_than,
            },
            max_charge_usd=posts_cap,
            max_items=posts_limit * 2,
        )
        budget.charge(result.cost_usd)

        batch = Batch(
            coverage={
                "page_url": page_url,
                "posts_newer_than": newer_than,
                "posts_per_run": posts_limit,
                "comments_per_post": comments_limit,
                "health_filter": bool(cfg["health_filter"]),
                "health_terms_version": HEALTH_TERMS_VERSION,
                "apify_runs": [{"actor": POSTS_ACTOR, "status": result.status}],
            }
        )
        if result.status != "SUCCEEDED":
            batch.partial_errors.append(f"Publications : course Apify {result.status}.")

        relevant: list[tuple[dict[str, Any], ItemIn]] = []
        newest = _parse_time(cursor.get("newest_post_at"))
        filtered_out = 0
        for post in result.items:
            if post.get("error") or (not post.get("postId") and not post.get("url")):
                batch.partial_errors.append(
                    f"Publication illisible : {str(post.get('error') or 'sans identifiant')[:200]}"
                )
                continue
            text = _post_text(post)
            published = _parse_time(post.get("time") or post.get("timestamp"))
            if published and (newest is None or published > newest):
                newest = published
            terms = health_terms_in(text)
            if cfg["health_filter"] and not terms:
                filtered_out += 1
                continue
            item = ItemIn(
                external_id=f"facebook:post:{post.get('postId') or post.get('url')}",
                raw_text=text,
                published_at=published,
                canonical_url=post.get("url"),
                author_kind=AuthorKind.ORGANISATION,
                author_org_name=_page_name(post),
                metrics={
                    k: v
                    for k, v in {
                        "reactions": _int(post.get("likes")),
                        "comments": _int(post.get("comments")),
                        "shares": _int(post.get("shares")),
                        "views": _int(post.get("viewsCount")),
                        "health_terms": terms,
                    }.items()
                    if v not in (None, [])
                },
            )
            batch.items.append(item)
            relevant.append((post, item))

        batch.coverage["posts_fetched"] = len(result.items)
        batch.coverage["posts_filtered_out"] = filtered_out
        if newest:
            batch.cursor_after = {"newest_post_at": newest.isoformat()}

        with_comments = [(p, i) for p, i in relevant if (_int(p.get("comments")) or 0) > 0]
        batch.coverage["posts_with_comments"] = len(with_comments)
        self._collect_comments(client, budget, with_comments, comments_limit, page_url, batch)
        batch.coverage["cost_usd"] = round(budget.spent_usd, 4)
        return batch

    def _collect_comments(
        self,
        client: ApifyClient,
        budget: Budget,
        posts: list[tuple[dict[str, Any], ItemIn]],
        limit: int,
        page_url: str,
        batch: Batch,
    ) -> None:
        if not posts or limit <= 0:
            return
        planned: list[tuple[dict[str, Any], ItemIn, float]] = []
        for post, item in posts:
            try:
                cap = budget.cap(MARGIN * (PRICE_START_USD + limit * PRICE_COMMENT_USD))
            except BudgetExhausted as exc:
                batch.partial_errors.append(str(exc))
                break
            budget.charge(cap)  # reserved now, corrected with the real cost below
            planned.append((post, item, cap))

        def run(post: dict[str, Any], cap: float):
            return client.run_actor(
                COMMENTS_ACTOR,
                {
                    "startUrls": [{"url": post["url"]}],
                    "resultsLimit": limit,
                    "includeNestedComments": False,
                },
                max_charge_usd=cap,
                max_items=limit * 2,
            )

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [(item, cap, pool.submit(run, post, cap)) for post, item, cap in planned]
            comments_total = 0
            for parent, cap, future in futures:
                try:
                    res = future.result()
                except ConnectorError as exc:
                    budget.charge(-cap)
                    batch.partial_errors.append(f"Commentaires : {exc}")
                    continue
                budget.charge(res.cost_usd - cap)
                batch.coverage["apify_runs"].append({"actor": COMMENTS_ACTOR, "status": res.status})
                comments = [
                    c
                    for c in res.items
                    if c.get("text") and not c.get("error") and (c.get("commentId") or c.get("id"))
                ]
                thread_names = sorted({n for c in comments for n in _commenter_names(c)})
                for c in comments:
                    is_page = _same_page(c.get("profileUrl"), page_url)
                    batch.items.append(
                        ItemIn(
                            external_id=(f"facebook:comment:{c.get('commentId') or c.get('id')}"),
                            raw_text=c["text"],
                            published_at=_parse_time(c.get("date")),
                            parent_external_id=parent.external_id,
                            author_kind=(
                                AuthorKind.ORGANISATION if is_page else AuthorKind.INDIVIDUAL
                            ),
                            author_org_name=parent.author_org_name if is_page else None,
                            known_names=[n for n in thread_names if n != parent.author_org_name],
                            metrics={
                                k: v
                                for k, v in {
                                    "likes": _int(c.get("likesCount")),
                                    "replies": _int(c.get("commentsCount")),
                                }.items()
                                if v is not None
                            },
                        )
                    )
                    comments_total += 1
            batch.coverage["comments_fetched"] = comments_total
