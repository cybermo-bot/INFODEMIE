from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import trafilatura
from pypdf import PdfReader

from .config import settings
from .llm import OllamaEmbedder
from .utils import chunk_text, clean_text, hash_text, load_json, read_jsonl, write_jsonl


@dataclass(slots=True)
class SourceDocument:
    title: str
    source_url: str
    text: str
    source_type: str


CHUNKS_PATH = settings.index_dir / "whitelist_chunks.jsonl"
EMBEDDINGS_PATH = settings.index_dir / "whitelist_embeddings.npy"
MANIFEST_PATH = settings.index_dir / "whitelist_manifest.json"


def _fetch_url_document(title: str, url: str) -> SourceDocument | None:
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        if not extracted:
            return None
        return SourceDocument(
            title=title,
            source_url=url,
            text=clean_text(extracted),
            source_type="url",
        )
    except Exception:
        return None


def _read_pdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    texts: list[str] = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return clean_text("\n".join(texts))


def _read_local_document(path: Path) -> SourceDocument | None:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = clean_text(path.read_text(encoding="utf-8", errors="ignore"))
    elif suffix == ".pdf":
        text = _read_pdf(path)
    else:
        return None
    if not text:
        return None
    return SourceDocument(
        title=path.stem,
        source_url=str(path),
        text=text,
        source_type="local_file",
    )


def load_whitelist_source_specs() -> list[dict[str, str]]:
    return load_json(settings.data_dir / "whitelist_urls.json", [])


def load_whitelist_documents() -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    for spec in load_whitelist_source_specs():
        title = spec.get("title", spec.get("url", "Official source"))
        url = spec.get("url", "")
        if not url:
            continue
        doc = _fetch_url_document(title, url)
        if doc:
            docs.append(doc)

    for path in sorted(settings.local_whitelist_dir.glob("*")):
        if path.is_file():
            doc = _read_local_document(path)
            if doc:
                docs.append(doc)
    return docs


def build_whitelist_index(force_rebuild: bool = False) -> dict[str, object]:
    if not force_rebuild and CHUNKS_PATH.exists() and EMBEDDINGS_PATH.exists():
        return load_whitelist_index()

    docs = load_whitelist_documents()
    chunks: list[dict[str, object]] = []
    texts_to_embed: list[str] = []
    for doc in docs:
        for idx, chunk in enumerate(chunk_text(doc.text, chunk_size=1200, overlap=250)):
            chunk_id = f"{hash_text(doc.source_url)}_{idx:03d}"
            row = {
                "chunk_id": chunk_id,
                "source_title": doc.title,
                "source_url": doc.source_url,
                "source_type": doc.source_type,
                "text": chunk,
            }
            chunks.append(row)
            texts_to_embed.append(chunk)

    embedder = OllamaEmbedder()
    embeddings = np.array(embedder.embed_texts(texts_to_embed), dtype=np.float32)

    write_jsonl(CHUNKS_PATH, chunks)
    np.save(EMBEDDINGS_PATH, embeddings)
    manifest = {
        "document_count": len(docs),
        "chunk_count": len(chunks),
        "llm_embed_model": settings.embed_model,
    }
    MANIFEST_PATH.write_text(__import__("json").dumps(manifest, indent=2), encoding="utf-8")
    return {
        "chunks": chunks,
        "embeddings": embeddings,
        "manifest": manifest,
    }


def load_whitelist_index() -> dict[str, object]:
    chunks = read_jsonl(CHUNKS_PATH)
    embeddings = np.load(EMBEDDINGS_PATH)
    manifest = load_json(MANIFEST_PATH, {})
    return {
        "chunks": chunks,
        "embeddings": embeddings,
        "manifest": manifest,
    }
