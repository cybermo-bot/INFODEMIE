"""Facebook public Pages and public groups through Apify actors.

Route `public_contested` (decisions D4, D17, D18): logged-out collection of a
small, hand-checked watch-list. Actors and fields checked against real runs on
2026-10-22:

- `apify/facebook-posts-scraper`: input `startUrls`, `resultsLimit` (posts per
  Page), `onlyPostsNewerThan`.
- `apify/facebook-groups-scraper`: input `startUrls`, `resultsLimit`,
  `viewOption`, `onlyPostsNewerThan`. Public groups only.
- `apify/facebook-comments-scraper`: input `startUrls` (post URLs),
  `resultsLimit`, `includeNestedComments`. Group posts return "Empty or private
  data" logged out, so groups give posts only.

Prices on the Apify free plan (checked 2026-10-22, same for both post actors):
0.005 USD per post plus 0.002 USD per post when a date filter is set (we always
set one), 0.0025 USD per comment, 0.001 USD per actor start. Comments are run
one post at a time so `resultsLimit` is unambiguously a per-post limit.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, ClassVar
from urllib.parse import urlsplit

from pnsi.collection.relevance import HEALTH_TERMS_VERSION, health_terms_in
from pnsi.connectors.apify import ActorResult, ApifyClient, Budget
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
GROUPS_ACTOR = "apify~facebook-groups-scraper"
COMMENTS_ACTOR = "apify~facebook-comments-scraper"
PRICE_POST_USD = 0.005
PRICE_DATE_FILTER_USD = 0.002
PRICE_COMMENT_USD = 0.0025
PRICE_START_USD = 0.001
MARGIN = 1.2

DEFAULTS: dict[str, Any] = {
    "posts_per_run": 10,
    "comments_per_post": 20,
    "first_run_lookback": "3 days",
    "health_filter": True,
}
GROUP_DEFAULTS: dict[str, Any] = {**DEFAULTS, "comments_per_post": 0}

FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com"}


def _split(url: str) -> tuple[str, str]:
    raw = url.strip()
    if "://" not in raw:
        raw = "https://" + raw
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    path = parts.path.strip("/")
    if host not in FACEBOOK_HOSTS or not path:
        raise ValueError("adresse Facebook attendue (https://www.facebook.com/...)")
    return path, parts.query


def normalize_page_url(url: str) -> str:
    """https://www.facebook.com/<page>, or ValueError when it is not a Facebook Page URL."""
    path, query = _split(url)
    if path.split("/")[0] in {"groups", "events", "watch", "share", "story.php", "photo"}:
        raise ValueError("une Page publique est attendue, pas un groupe ni une publication")
    keep = f"?{query}" if path == "profile.php" and query else ""
    return f"https://www.facebook.com/{path}{keep}"


def normalize_group_url(url: str) -> str:
    """https://www.facebook.com/groups/<id or name>, or ValueError."""
    path, _query = _split(url)
    segments = path.split("/")
    if segments[0] != "groups" or len(segments) < 2 or not segments[1]:
        raise ValueError("un groupe est attendu (https://www.facebook.com/groups/...)")
    if len(segments) > 2:
        raise ValueError("l'adresse du groupe est attendue, pas celle d'une publication")
    return f"https://www.facebook.com/groups/{segments[1]}"


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


def _metrics(**values: Any) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v not in (None, [])}


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


def _group_post_text(post: dict[str, Any]) -> str:
    text = post.get("text") or ""
    if text:
        return text
    shared = post.get("sharedPost")
    if isinstance(shared, dict) and shared.get("text"):
        return shared["text"]
    return post.get("title") or ""


def _group_post_names(post: dict[str, Any]) -> list[str]:
    """Every person's name the group post carries: author, tagged people, shared author."""
    names: list[Any] = []
    if isinstance(post.get("user"), dict):
        names.append(post["user"].get("name"))
    for ref in [*(post.get("textReferences") or []), *(post.get("collaborators") or [])]:
        if isinstance(ref, dict):
            names += [ref.get("short_name"), ref.get("name")]
    shared = post.get("sharedPost")
    if isinstance(shared, dict):
        for who in (shared.get("user"), shared.get("pageName")):
            if isinstance(who, dict):
                names.append(who.get("name"))
    return sorted({n.strip() for n in names if isinstance(n, str) and n.strip()})


def _commenter_names(comment: dict[str, Any]) -> list[str]:
    names = [comment.get("profileName"), comment.get("name")]
    author = comment.get("author")
    if isinstance(author, dict):
        names.append(author.get("name"))
    return [n for n in names if n]


def _billed(result: ActorResult, items: int, per_item_usd: float) -> float:
    """The run's cost, never less than what the received items must have cost."""
    return max(result.cost_usd, PRICE_START_USD + items * per_item_usd)


class _FacebookApify:
    """Posts of one Facebook source, health filter, then comments of relevant posts."""

    key: ClassVar[str]
    route: ClassVar[CollectionRoute] = CollectionRoute.PUBLIC_CONTESTED
    basis: ClassVar[str]
    actor: ClassVar[str]
    url_field: ClassVar[str]
    defaults: ClassVar[dict[str, Any]]

    def __init__(self, settings: Settings, client_factory=None) -> None:
        self.settings = settings
        self._client_factory = client_factory or (
            lambda: ApifyClient(
                settings.apify_token.get_secret_value() if settings.apify_token else None
            )
        )

    def validate_config(self, settings: Settings) -> ConfigStatus:
        return ConfigStatus.OK if settings.apify_token else ConfigStatus.NOT_CONFIGURED

    @staticmethod
    def normalize(url: str) -> str:
        raise NotImplementedError

    def run_input(self, url: str, limit: int, newer_than: str) -> dict[str, Any]:
        raise NotImplementedError

    def to_item(self, post: dict[str, Any], text: str, published: datetime | None,
                terms: list[str]) -> ItemIn:  # fmt: skip
        raise NotImplementedError

    def fetch(self, source: Source, cursor: dict[str, Any] | None) -> Batch:
        cfg = {**self.defaults, **(source.config or {})}
        url = self.normalize(cfg[self.url_field])
        client = self._client_factory()
        try:
            return self._fetch(client, cfg, url, cursor or {})
        finally:
            client.close()

    def _fetch(
        self, client: ApifyClient, cfg: dict[str, Any], url: str, cursor: dict[str, Any]
    ) -> Batch:
        budget = client.budget(self.settings.apify_max_spend_usd)
        posts_limit = int(cfg["posts_per_run"])
        comments_limit = int(cfg["comments_per_post"])
        newer_than = cursor.get("newest_post_at") or cfg["first_run_lookback"]
        per_post = PRICE_POST_USD + PRICE_DATE_FILTER_USD

        posts_cap = budget.cap(MARGIN * (PRICE_START_USD + posts_limit * per_post))
        result = client.run_actor(
            self.actor,
            self.run_input(url, posts_limit, newer_than),
            max_charge_usd=posts_cap,
            max_items=posts_limit * 2,
        )

        batch = Batch(
            coverage={
                self.url_field: url,
                "posts_newer_than": newer_than,
                "posts_per_run": posts_limit,
                "comments_per_post": comments_limit,
                "health_filter": bool(cfg["health_filter"]),
                "health_terms_version": HEALTH_TERMS_VERSION,
                "apify_runs": [{"actor": self.actor, "status": result.status}],
            }
        )
        if result.status != "SUCCEEDED":
            batch.partial_errors.append(f"Publications : course Apify {result.status}.")

        relevant: list[tuple[dict[str, Any], ItemIn]] = []
        newest = _parse_time(cursor.get("newest_post_at"))
        filtered_out = 0
        received = 0
        for post in result.items:
            if post.get("error") or not (post.get("postId") or post.get("id") or post.get("url")):
                if post.get("error") == "no_items":
                    # Apify's answer for an empty window as well as for a private source.
                    batch.coverage["no_items"] = True
                    continue
                batch.partial_errors.append(
                    f"Publication illisible : {str(post.get('error') or 'sans identifiant')[:200]}"
                )
                continue
            received += 1
            text = self.post_text(post)
            published = _parse_time(post.get("time") or post.get("timestamp"))
            if published and (newest is None or published > newest):
                newest = published
            terms = health_terms_in(text)
            if cfg["health_filter"] and not terms:
                filtered_out += 1
                continue
            item = self.to_item(post, text, published, terms)
            batch.items.append(item)
            relevant.append((post, item))
        budget.charge(_billed(result, received, per_post))

        batch.coverage["posts_fetched"] = received
        batch.coverage["posts_filtered_out"] = filtered_out
        if newest:
            batch.cursor_after = {"newest_post_at": newest.isoformat()}

        with_comments = [(p, i) for p, i in relevant if (self.comment_count(p) or 0) > 0]
        batch.coverage["posts_with_comments"] = len(with_comments)
        self._collect_comments(client, budget, with_comments, comments_limit, url, batch)
        batch.coverage["cost_usd"] = round(budget.spent_usd, 4)
        return batch

    def post_text(self, post: dict[str, Any]) -> str:
        return _post_text(post)

    def comment_count(self, post: dict[str, Any]) -> int | None:
        return _int(post.get("comments"))

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
                batch.coverage["apify_runs"].append({"actor": COMMENTS_ACTOR, "status": res.status})
                comments = [
                    c
                    for c in res.items
                    if c.get("text") and not c.get("error") and (c.get("commentId") or c.get("id"))
                ]
                budget.charge(_billed(res, len(comments), PRICE_COMMENT_USD) - cap)
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
                            metrics=_metrics(
                                likes=_int(c.get("likesCount")),
                                replies=_int(c.get("commentsCount")),
                            ),
                        )
                    )
                    comments_total += 1
            batch.coverage["comments_fetched"] = comments_total


class FacebookPagesApify(_FacebookApify):
    key = "facebook_pages_apify"
    actor = POSTS_ACTOR
    url_field = "page_url"
    defaults = DEFAULTS
    basis = (
        "Collecte sans connexion de Pages Facebook publiques d'une liste vérifiée, via les "
        "acteurs Apify facebook-posts-scraper et facebook-comments-scraper. Position "
        "juridique contestée par Meta (décision D4) : liste restreinte, rythme modéré."
    )

    @staticmethod
    def normalize(url: str) -> str:
        return normalize_page_url(url)

    def run_input(self, url: str, limit: int, newer_than: str) -> dict[str, Any]:
        return {
            "startUrls": [{"url": url}],
            "resultsLimit": limit,
            "onlyPostsNewerThan": newer_than,
        }

    def to_item(self, post: dict[str, Any], text: str, published: datetime | None,
                terms: list[str]) -> ItemIn:  # fmt: skip
        return ItemIn(
            external_id=f"facebook:post:{post.get('postId') or post.get('url')}",
            raw_text=text,
            published_at=published,
            canonical_url=post.get("url"),
            author_kind=AuthorKind.ORGANISATION,
            author_org_name=_page_name(post),
            metrics=_metrics(
                reactions=_int(post.get("likes")),
                comments=_int(post.get("comments")),
                shares=_int(post.get("shares")),
                views=_int(post.get("viewsCount")),
                health_terms=terms,
            ),
        )


class FacebookGroupsApify(_FacebookApify):
    """Public groups: posts written by private individuals, so nothing points back to them.

    The author, tagged people and collaborators are handed over for redaction, and
    no post URL is kept (the group URL stays on the source). Comments are not
    reachable logged out.
    """

    key = "facebook_groups_apify"
    actor = GROUPS_ACTOR
    url_field = "group_url"
    defaults = GROUP_DEFAULTS
    basis = (
        "Collecte sans connexion de groupes Facebook publics d'une liste vérifiée, via "
        "l'acteur Apify facebook-groups-scraper. Les auteurs sont des particuliers : leur "
        "nom, les personnes mentionnées et les liens sont retirés avant stockage, aucun lien "
        "vers la publication n'est conservé. Commentaires inaccessibles sans connexion. "
        "Position juridique contestée par Meta (décisions D4 et D18)."
    )

    @staticmethod
    def normalize(url: str) -> str:
        return normalize_group_url(url)

    def run_input(self, url: str, limit: int, newer_than: str) -> dict[str, Any]:
        return {
            "startUrls": [{"url": url}],
            "resultsLimit": limit,
            "viewOption": "CHRONOLOGICAL",
            "onlyPostsNewerThan": newer_than,
        }

    def post_text(self, post: dict[str, Any]) -> str:
        return _group_post_text(post)

    def _collect_comments(self, client, budget, posts, limit, page_url, batch) -> None:
        # Checked 2026-10-22: "Empty or private data" for group posts, so never paid for.
        batch.coverage["comments"] = "non accessibles sans connexion pour un groupe"

    def comment_count(self, post: dict[str, Any]) -> int | None:
        return _int(post.get("commentsCount"))

    def to_item(self, post: dict[str, Any], text: str, published: datetime | None,
                terms: list[str]) -> ItemIn:  # fmt: skip
        post_id = post.get("legacyId") or post.get("id") or post.get("url")
        return ItemIn(
            external_id=f"facebook:group-post:{post_id}",
            raw_text=text,
            published_at=published,
            author_kind=AuthorKind.INDIVIDUAL,
            known_names=_group_post_names(post),
            metrics=_metrics(
                reactions=_int(post.get("likesCount")),
                comments=_int(post.get("commentsCount")),
                shares=_int(post.get("sharesCount")),
                views=_int(post.get("videoPostViewCount")),
                health_terms=terms,
            ),
        )
