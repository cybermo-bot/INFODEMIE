from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")
    embed_model: str = os.getenv("EMBED_MODEL", "bge-m3:567m-fp16")
    output_language: str = os.getenv("OUTPUT_LANGUAGE", "fr")

    top_k_evidence: int = int(os.getenv("TOP_K_EVIDENCE", "6"))
    top_k_context: int = int(os.getenv("TOP_K_CONTEXT", "6"))
    max_feed_items: int = int(os.getenv("MAX_FEED_ITEMS", "12"))
    max_discovery_items: int = int(os.getenv("MAX_DISCOVERY_ITEMS", "20"))
    news_country: str = os.getenv("NEWS_COUNTRY", "TN")
    news_language: str = os.getenv("NEWS_LANGUAGE", "fr")
    bluesky_api_base: str = os.getenv("BLUESKY_API_BASE", "https://public.api.bsky.app")

    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    index_dir: Path = BASE_DIR / "index"
    runs_dir: Path = BASE_DIR / "runs"
    local_whitelist_dir: Path = BASE_DIR / "local_whitelist"


settings = Settings()

for directory in [
    settings.data_dir,
    settings.index_dir,
    settings.runs_dir,
    settings.local_whitelist_dir,
]:
    directory.mkdir(parents=True, exist_ok=True)
