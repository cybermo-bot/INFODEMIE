from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import numpy as np
import requests

from .collector import fetch_article_text
from .config import settings
from .llm import OllamaEmbedder
from .schemas import EvidenceChunk, InputItem
from .utils import (
    chunk_text,
    clean_text,
    cosine_similarity_matrix,
    hash_text,
    load_json,
    read_jsonl,
    write_jsonl,
)


DISCOVERY_ITEMS_PATH = settings.data_dir / "discovery_items.jsonl"
DISCOVERY_CHUNKS_PATH = settings.index_dir / "discovery_chunks.jsonl"
DISCOVERY_EMBEDDINGS_PATH = settings.index_dir / "discovery_embeddings.npy"
DISCOVERY_MANIFEST_PATH = settings.index_dir / "discovery_manifest.json"

_HEADERS = {"User-Agent": "OMS-Tunisia-Infodemie-Demo/0.2"}


# ── Google News RSS ────────────────────────────────────────────────────────────
def _google_news_rss_url(query: str, language: str | None = None, country: str | None = None) -> str:
    language = (language or settings.news_language).lower()
    country = (country or settings.news_country).upper()
    q = quote_plus(f"{query} when:7d")
    return f"https://news.google.com/rss/search?q={q}&hl={language}&gl={country}&ceid={country}:{language}"


def collect_news_query_items(
    query: str,
    max_items: int | None = None,
    language: str | None = None,
    country: str | None = None,
) -> list[InputItem]:
    if max_items is None:
        max_items = max(1, settings.max_discovery_items // 2)
    parsed = feedparser.parse(_google_news_rss_url(query=query, language=language, country=country))
    items: list[InputItem] = []
    seen: set[str] = set()
    for entry in getattr(parsed, "entries", [])[:max_items]:
        title = clean_text(entry.get("title", ""))
        url = entry.get("link", "")
        body = fetch_article_text(url)
        signature = hash_text(f"news::{title}::{url}")
        if signature in seen:
            continue
        seen.add(signature)
        items.append(
            InputItem(
                title=title,
                text=body or title,
                url=url,
                source="google_news_search",
                published=entry.get("published", "") or entry.get("updated", ""),
                source_type="news_search",
                metadata={
                    "query": query,
                    "language": language or settings.news_language,
                    "country": country or settings.news_country,
                },
            )
        )
    return items


# ── Bluesky ────────────────────────────────────────────────────────────────────
def collect_bluesky_query_items(query: str, max_items: int | None = None) -> list[InputItem]:
    if max_items is None:
        max_items = max(1, settings.max_discovery_items // 2)
    endpoint = settings.bluesky_api_base.rstrip("/") + "/xrpc/app.bsky.feed.searchPosts"
    params = {"q": query, "limit": min(max_items, 100), "sort": "latest"}
    try:
        response = requests.get(endpoint, params=params, headers=_HEADERS, timeout=25)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    items: list[InputItem] = []
    seen: set[str] = set()
    for post in payload.get("posts", [])[:max_items]:
        record = post.get("record", {}) or {}
        author = post.get("author", {}) or {}
        text = clean_text(record.get("text", ""))
        title = clean_text(text[:140])
        uri = post.get("uri", "")
        handle = author.get("handle", "")
        if not text:
            continue
        signature = hash_text(f"bluesky::{uri or text}")
        if signature in seen:
            continue
        seen.add(signature)
        likes = post.get("likeCount", 0)
        replies = post.get("replyCount", 0)
        reposts = post.get("repostCount", 0)
        items.append(
            InputItem(
                title=title or f"Bluesky post by @{handle}",
                text=text,
                url=uri,
                source=f"bluesky:@{handle}" if handle else "bluesky",
                published=post.get("indexedAt", ""),
                source_type="bluesky",
                metadata={
                    "query": query,
                    "author_handle": handle,
                    "author_display_name": author.get("displayName", ""),
                    "like_count": likes,
                    "reply_count": replies,
                    "repost_count": reposts,
                    "engagement": likes + replies + reposts,
                },
            )
        )
    return items


# ── Reddit public search ──────────────────────────────────────────────────────
def collect_reddit_query_items(query: str, max_items: int | None = None) -> list[InputItem]:
    """Search Reddit via the public JSON API (no key needed)."""
    if max_items is None:
        max_items = 6
    url = "https://www.reddit.com/search.json"
    params = {"q": query, "sort": "relevance", "t": "week", "limit": min(max_items, 25)}
    try:
        response = requests.get(url, params=params, headers={
            "User-Agent": "OMS-Tunisia-Infodemie-Demo/0.2 (health research)"
        }, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    items: list[InputItem] = []
    seen: set[str] = set()
    for child in data.get("data", {}).get("children", [])[:max_items]:
        post = child.get("data", {})
        title = clean_text(post.get("title", ""))
        selftext = clean_text(post.get("selftext", ""))
        permalink = post.get("permalink", "")
        full_url = f"https://www.reddit.com{permalink}" if permalink else ""
        subreddit = post.get("subreddit", "")
        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)

        body = selftext or title
        if not body:
            continue
        signature = hash_text(f"reddit::{title}::{permalink}")
        if signature in seen:
            continue
        seen.add(signature)

        items.append(
            InputItem(
                title=title,
                text=body[:3000],
                url=full_url,
                source=f"reddit:r/{subreddit}",
                published=datetime.fromtimestamp(
                    post.get("created_utc", 0), tz=timezone.utc
                ).isoformat() if post.get("created_utc") else "",
                source_type="reddit",
                metadata={
                    "query": query,
                    "subreddit": subreddit,
                    "score": score,
                    "num_comments": num_comments,
                    "engagement": score + num_comments,
                    "author": post.get("author", ""),
                },
            )
        )
    return items


# ── DuckDuckGo news search ────────────────────────────────────────────────────
def collect_ddg_news_items(query: str, max_items: int | None = None) -> list[InputItem]:
    """Search DuckDuckGo news via the duckduckgo-search package (no API key)."""
    if max_items is None:
        max_items = 6
    try:
        from duckduckgo_search import DDGS
        results = DDGS().news(keywords=query, max_results=max_items, region="wt-wt")
    except Exception:
        return []

    items: list[InputItem] = []
    seen: set[str] = set()
    for r in results[:max_items]:
        title = clean_text(r.get("title", ""))
        url = r.get("url", "") or r.get("link", "")
        body = clean_text(r.get("body", "")) or title
        source_name = r.get("source", "DuckDuckGo News")
        date_str = r.get("date", "")

        signature = hash_text(f"ddg::{title}::{url}")
        if signature in seen:
            continue
        seen.add(signature)

        items.append(
            InputItem(
                title=title,
                text=body[:3000],
                url=url,
                source=f"ddg_news:{source_name}",
                published=date_str,
                source_type="ddg_news",
                metadata={"query": query, "source": source_name},
            )
        )
    return items


# ── ProMED RSS ────────────────────────────────────────────────────────────────
def collect_promed_items(max_items: int | None = None) -> list[InputItem]:
    """Fetch ProMED epidemic alert RSS - official WHO-adjacent source."""
    if max_items is None:
        max_items = 8
    urls_to_try = [
        "https://promedmail.org/promed-rss/",
        "https://promedmail.org/feed/",
        "https://promedmail.org/promed-posts/feed/",
    ]
    parsed = None
    for url in urls_to_try:
        try:
            parsed = feedparser.parse(url)
            if getattr(parsed, "entries", []):
                break
        except Exception:
            continue
    if not parsed or not getattr(parsed, "entries", []):
        return []

    from bs4 import BeautifulSoup

    items: list[InputItem] = []
    seen: set[str] = set()
    for entry in parsed.entries[:max_items]:
        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "")
        summary_html = entry.get("summary", "") or entry.get("description", "")
        summary = clean_text(BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True))
        pub = entry.get("published", "") or entry.get("updated", "")

        signature = hash_text(f"promed::{title}::{link}")
        if signature in seen:
            continue
        seen.add(signature)

        items.append(
            InputItem(
                title=title,
                text=summary or title,
                url=link,
                source="ProMED",
                published=pub,
                source_type="promed",
                metadata={"feed": "ProMED-mail"},
            )
        )
    return items


# ── Telegram public channels via RSShub ────────────────────────────────────────
TELEGRAM_HEALTH_CHANNELS = [
    "WHO",
]


def collect_telegram_items(max_items: int | None = None, channels: list[str] | None = None) -> list[InputItem]:
    """Fetch Telegram public channel posts via RSSHub bridge (no API key needed)."""
    if max_items is None:
        max_items = 4
    if channels is None:
        channels = TELEGRAM_HEALTH_CHANNELS

    from bs4 import BeautifulSoup

    items: list[InputItem] = []
    seen: set[str] = set()

    for channel in channels:
        rss_url = f"https://rsshub.app/telegram/channel/{channel}"
        try:
            parsed = feedparser.parse(rss_url)
        except Exception:
            continue

        for entry in getattr(parsed, "entries", [])[:max_items]:
            title = clean_text(entry.get("title", ""))
            link = entry.get("link", "")
            summary_html = entry.get("summary", "") or entry.get("description", "")
            summary = clean_text(BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True))
            pub = entry.get("published", "") or entry.get("updated", "")

            body = summary or title
            if not body:
                continue
            signature = hash_text(f"telegram::{channel}::{title}::{link}")
            if signature in seen:
                continue
            seen.add(signature)

            items.append(
                InputItem(
                    title=title or f"Telegram @{channel}",
                    text=body[:3000],
                    url=link,
                    source=f"telegram:@{channel}",
                    published=pub,
                    source_type="telegram",
                    metadata={"channel": channel},
                )
            )
    return items


# ── Main discovery orchestrator ────────────────────────────────────────────────
def collect_discovery_items(
    query: str,
    include_news: bool = True,
    include_bluesky: bool = True,
    include_reddit: bool = True,
    include_ddg: bool = True,
    include_promed: bool = True,
    include_telegram: bool = False,
    max_items_per_source: int = 8,
    language: str | None = None,
    country: str | None = None,
) -> list[InputItem]:
    items: list[InputItem] = []
    source_counts: dict[str, int] = {}

    def _collect(name: str, fn, **kwargs):
        try:
            result = fn(**kwargs)
            items.extend(result)
            source_counts[name] = len(result)
        except Exception:
            source_counts[name] = 0

    if include_news:
        _collect("google_news", collect_news_query_items,
                 query=query, max_items=max_items_per_source, language=language, country=country)
    if include_bluesky:
        _collect("bluesky", collect_bluesky_query_items,
                 query=query, max_items=max_items_per_source)
    if include_reddit:
        _collect("reddit", collect_reddit_query_items,
                 query=query, max_items=max_items_per_source)
    if include_ddg:
        _collect("ddg_news", collect_ddg_news_items,
                 query=query, max_items=max_items_per_source)
    if include_promed:
        _collect("promed", collect_promed_items,
                 max_items=max_items_per_source)
    if include_telegram:
        _collect("telegram", collect_telegram_items,
                 max_items=max_items_per_source)

    # Deduplicate
    deduped: list[InputItem] = []
    seen: set[str] = set()
    for item in items:
        signature = discovery_item_id(item)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(item)

    # Attach source counts to the first item's metadata (for UI display)
    for item in deduped:
        meta = dict(item.metadata) if item.metadata else {}
        meta["_source_counts"] = source_counts
        item.metadata = meta
        break  # Only on first item

    return deduped


def get_source_counts(items: list[InputItem]) -> dict[str, int]:
    """Extract source type breakdown from a list of discovery items."""
    counts: dict[str, int] = {}
    for item in items:
        st = getattr(item, "source_type", "unknown")
        counts[st] = counts.get(st, 0) + 1
    return counts


# ── Persistence and indexing (unchanged) ──────────────────────────────────────

def discovery_item_id(item: InputItem | dict) -> str:
    if isinstance(item, InputItem):
        payload = item.model_dump()
    else:
        payload = dict(item)
    basis = clean_text(
        f"{payload.get('source_type', '')}::{payload.get('url', '')}::{payload.get('title', '')}::{payload.get('text', '')[:250]}"
    )
    return hash_text(basis)


def _serialize_item(item: InputItem) -> dict:
    payload = item.model_dump()
    payload["item_id"] = discovery_item_id(item)
    payload["stored_at_utc"] = datetime.now(timezone.utc).isoformat()
    return payload


def append_discovery_items(items: Iterable[InputItem]) -> dict[str, int]:
    existing = read_jsonl(DISCOVERY_ITEMS_PATH)
    existing_ids = {row.get("item_id") for row in existing}
    new_rows: list[dict] = []
    for item in items:
        row = _serialize_item(item)
        if row["item_id"] in existing_ids:
            continue
        existing_ids.add(row["item_id"])
        new_rows.append(row)

    if new_rows:
        merged = existing + new_rows
        write_jsonl(DISCOVERY_ITEMS_PATH, merged)
    return {"added": len(new_rows), "total": len(existing) + len(new_rows)}


def load_discovery_items() -> list[InputItem]:
    return [InputItem(**row) for row in read_jsonl(DISCOVERY_ITEMS_PATH)]


def build_discovery_index(force_rebuild: bool = False) -> dict[str, object]:
    if not force_rebuild and DISCOVERY_CHUNKS_PATH.exists() and DISCOVERY_EMBEDDINGS_PATH.exists():
        return load_discovery_index()

    items = load_discovery_items()
    chunks: list[dict[str, object]] = []
    texts_to_embed: list[str] = []
    for item in items:
        item_id = discovery_item_id(item)
        text = clean_text(f"Title: {item.title}\nSource: {item.source}\nText: {item.text}")
        for idx, chunk in enumerate(chunk_text(text, chunk_size=1000, overlap=180)):
            row = {
                "chunk_id": f"{item_id}_{idx:03d}",
                "source_title": item.title or item.source,
                "source_url": item.url,
                "source_type": item.source_type,
                "text": chunk,
            }
            chunks.append(row)
            texts_to_embed.append(chunk)

    if texts_to_embed:
        embedder = OllamaEmbedder()
        embeddings = np.array(embedder.embed_texts(texts_to_embed), dtype=np.float32)
    else:
        embeddings = np.empty((0, 0), dtype=np.float32)

    write_jsonl(DISCOVERY_CHUNKS_PATH, chunks)
    np.save(DISCOVERY_EMBEDDINGS_PATH, embeddings)
    manifest = {
        "item_count": len(items),
        "chunk_count": len(chunks),
        "embed_model": settings.embed_model,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    DISCOVERY_MANIFEST_PATH.write_text(__import__("json").dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"chunks": chunks, "embeddings": embeddings, "manifest": manifest}


def load_discovery_index() -> dict[str, object]:
    chunks = read_jsonl(DISCOVERY_CHUNKS_PATH)
    embeddings = np.load(DISCOVERY_EMBEDDINGS_PATH)
    manifest = load_json(DISCOVERY_MANIFEST_PATH, {})
    return {"chunks": chunks, "embeddings": embeddings, "manifest": manifest}


def search_discovery(query: str, top_k: int | None = None) -> list[EvidenceChunk]:
    if top_k is None:
        top_k = settings.top_k_context

    try:
        index = load_discovery_index()
    except FileNotFoundError:
        return []

    chunks = index["chunks"]
    embeddings = index["embeddings"]
    if not chunks or len(embeddings) == 0:
        return []

    embedder = OllamaEmbedder()
    query_vector = np.array(embedder.embed_query(query), dtype=np.float32)
    if query_vector.size == 0:
        return []

    scores = cosine_similarity_matrix(query_vector, embeddings)
    top_indices = np.argsort(scores)[::-1][:top_k]

    output: list[EvidenceChunk] = []
    for idx in top_indices:
        row = chunks[int(idx)]
        output.append(
            EvidenceChunk(
                chunk_id=str(row["chunk_id"]),
                source_title=str(row["source_title"]),
                source_url=str(row.get("source_url", "")),
                source_type=str(row.get("source_type", "")),
                text=str(row["text"]),
                score=float(scores[int(idx)]),
            )
        )
    return output
