"""Recent URL history for theOne."""

from __future__ import annotations

import json
from pathlib import Path

from theone.config import default_config_path

MAX_HISTORY = 20


def default_history_path() -> Path:
    return default_config_path().parent / "history.json"


def load_history(path: Path | None = None) -> list[str]:
    history_path = path or default_history_path()
    if not history_path.is_file():
        return []
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data if isinstance(item, str) and item.strip()]


def save_history(urls: list[str], path: Path | None = None) -> Path:
    history_path = path or default_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned: list[str] = []
    for url in urls:
        url = url.strip()
        if url and url not in cleaned:
            cleaned.append(url)
        if len(cleaned) >= MAX_HISTORY:
            break
    history_path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
    return history_path


def push_history(url: str, path: Path | None = None) -> list[str]:
    url = url.strip()
    if not url:
        return load_history(path)
    existing = [u for u in load_history(path) if u != url]
    updated = [url, *existing][:MAX_HISTORY]
    save_history(updated, path)
    return updated
