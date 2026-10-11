from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import settings


FEEDBACK_PATH = settings.runs_dir / "feedback.jsonl"


def new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{timestamp}_{uuid4().hex[:8]}"


def save_run(state: dict[str, Any], run_id: str | None = None) -> str:
    run_id = run_id or state.get("run_id") or new_run_id()
    path = settings.runs_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        **state,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_id


def save_feedback(run_id: str, decision: str, notes: str = "") -> None:
    row = {
        "run_id": run_id,
        "decision": decision,
        "notes": notes,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
