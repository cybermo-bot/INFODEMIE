from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np

HEALTH_KEYWORDS = {
    "vaccin",
    "vaccination",
    "vaccine",
    "vaccines",
    "rougeole",
    "measles",
    "grippe",
    "influenza",
    "covid",
    "cholera",
    "virus",
    "bacterie",
    "bacteria",
    "antibiotique",
    "antibiotic",
    "fievre",
    "fever",
    "rash",
    "epidemie",
    "epidemic",
    "pandemie",
    "pandemic",
    "sante",
    "health",
    "immunite",
    "immunity",
    "autisme",
    "autism",
    "doaa",
    "dawa",
    "medecin",
    "doctor",
    "symptome",
    "symptom",
    "traitement",
    "treatment",
    "infection",
    "infectious",
    "لقاح",
    "صحة",
    "وباء",
    "حمى",
    "دواء",
}


def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start = max(0, end - overlap)
    return chunks


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def cosine_similarity_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query_norm = np.linalg.norm(query)
    matrix_norm = np.linalg.norm(matrix, axis=1)
    denom = np.maximum(matrix_norm * max(query_norm, 1e-12), 1e-12)
    return np.dot(matrix, query) / denom


def keyword_health_score(text: str) -> float:
    text = clean_text(text).lower()
    if not text:
        return 0.0
    hits = sum(1 for keyword in HEALTH_KEYWORDS if keyword in text)
    score = min(1.0, hits / 5.0)
    return round(score, 3)


def short_snippet(text: str, max_chars: int = 220) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_language_code(value: str) -> str:
    value = (value or "").lower().strip()
    if value in {"fr", "french"}:
        return "fr"
    if value in {"en", "english"}:
        return "en"
    if value in {"ar", "arabic"}:
        return "ar"
    if value in {"mixed", "mix"}:
        return "mixed"
    return "unknown"
