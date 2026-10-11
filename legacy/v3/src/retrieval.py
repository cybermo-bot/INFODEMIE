from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from .config import settings
from .llm import OllamaEmbedder
from .schemas import EvidenceChunk
from .utils import cosine_similarity_matrix, load_json, read_jsonl
from .whitelist import build_whitelist_index, load_whitelist_index


def _search_embedded_index(chunks: list[dict], embeddings: np.ndarray, query: str, top_k: int) -> list[EvidenceChunk]:
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


def search_whitelist(query: str, top_k: int | None = None, force_rebuild: bool = False) -> list[EvidenceChunk]:
    if top_k is None:
        top_k = settings.top_k_evidence

    try:
        index = build_whitelist_index(force_rebuild=force_rebuild) if force_rebuild else load_whitelist_index()
    except FileNotFoundError:
        index = build_whitelist_index(force_rebuild=True)

    return _search_embedded_index(index["chunks"], index["embeddings"], query=query, top_k=top_k)
