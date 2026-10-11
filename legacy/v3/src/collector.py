from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Iterable

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup

from .config import settings
from .schemas import InputItem
from .utils import clean_text, hash_text, load_json, short_snippet


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


def load_monitor_feeds() -> list[dict[str, str]]:
    return load_json(settings.data_dir / "monitor_feeds.json", [])


def fetch_article_text(url: str, timeout: int = 20) -> str:
    if not url:
        return ""
    headers = {"User-Agent": USER_AGENT}
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if extracted:
                return clean_text(extracted)
    except Exception:
        pass

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        return clean_text(" ".join(paragraphs))
    except Exception:
        return ""


def item_from_url(url: str, title: str = "", source: str = "url_paste") -> InputItem:
    body = fetch_article_text(url)
    return InputItem(
        title=clean_text(title) or clean_text(url),
        text=body or clean_text(title) or clean_text(url),
        url=url,
        source=source,
        source_type="url",
    )


def _feed_entries_to_items(parsed: object, source_name: str, source_type: str, max_items: int) -> list[InputItem]:
    items: list[InputItem] = []
    seen: set[str] = set()
    for entry in getattr(parsed, "entries", [])[:max_items]:
        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "")
        summary_html = entry.get("summary", "") or entry.get("description", "")
        summary = clean_text(BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True))
        article_text = fetch_article_text(link)
        body = article_text or summary or title
        signature = hash_text(title + link + source_name)
        if signature in seen:
            continue
        seen.add(signature)
        items.append(
            InputItem(
                title=title,
                text=body,
                url=link,
                source=source_name,
                published=entry.get("published", "") or entry.get("updated", ""),
                source_type=source_type,
            )
        )
    return items


def fetch_feed_items(max_items: int | None = None) -> list[InputItem]:
    feeds = load_monitor_feeds()
    if max_items is None:
        max_items = settings.max_feed_items

    items: list[InputItem] = []
    for feed in feeds:
        parsed = feedparser.parse(feed["url"])
        items.extend(
            _feed_entries_to_items(
                parsed=parsed,
                source_name=feed.get("name", "feed"),
                source_type="rss",
                max_items=int(feed.get("limit", 5)),
            )
        )
        if len(items) >= max_items:
            return items[:max_items]
    return items[:max_items]


def load_demo_claims() -> list[InputItem]:
    raw_rows = load_json(settings.data_dir / "demo_claims.json", [])
    return [InputItem(**row) for row in raw_rows]


def read_csv_items_from_text(csv_text: str, source_name: str = "uploaded_csv") -> list[InputItem]:
    rows: list[InputItem] = []
    handle = StringIO(csv_text)
    reader = csv.DictReader(handle)
    for row in reader:
        text = clean_text(row.get("text", ""))
        if not text:
            continue
        rows.append(
            InputItem(
                title=clean_text(row.get("title", "")),
                text=text,
                url=clean_text(row.get("url", "")),
                source=clean_text(row.get("source", source_name)) or source_name,
                published=clean_text(row.get("published", "")),
                source_type="csv",
                metadata={"raw_row": row},
            )
        )
    return rows


def read_csv_items_from_file(path: str | Path) -> list[InputItem]:
    path = Path(path)
    if not path.exists():
        return []
    csv_text = path.read_text(encoding="utf-8")
    return read_csv_items_from_text(csv_text, source_name=path.name)


def items_to_table(items: Iterable[InputItem]) -> list[dict[str, str]]:
    table: list[dict[str, str]] = []
    for item in items:
        table.append(
            {
                "title": item.title,
                "source": item.source,
                "source_type": item.source_type,
                "published": item.published,
                "preview": short_snippet(item.text),
                "url": item.url,
            }
        )
    return table
