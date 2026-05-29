from __future__ import annotations

from pathlib import Path
import json

from .models import ensure_parent, now_iso, stable_url_hash


class IngestionStateStore:
    """Persistent state store tracking URL ingestion progress.

    Uses a JSON file to track each URL's processing status across pipeline
    runs, enabling resume and skip-already-processed behavior.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data = self._load()

    def is_processed(self, url: str) -> bool:
        record = self.get_url(url)
        return record.get("status") in {"llm_done", "completed", "adaptation_rejected", "permanent_failed"}

    def get_url(self, url: str) -> dict:
        return self._data["urls"].get(stable_url_hash(url), {})

    def update_url(self, url: str, **fields) -> dict:
        key = stable_url_hash(url)
        record = self._data["urls"].get(key, {"url": url, "created_at": now_iso()})
        record.update(fields)
        record["updated_at"] = now_iso()
        self._data["urls"][key] = record
        self.save()
        return record

    def list_records(self) -> list[dict]:
        return list(self._data["urls"].values())

    def save(self) -> None:
        ensure_parent(self.path)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> dict:
        if not self.path.exists():
            return {"schema_version": 1, "urls": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"schema_version": 1, "urls": {}}
        if not isinstance(data, dict):
            return {"schema_version": 1, "urls": {}}
        data.setdefault("schema_version", 1)
        data.setdefault("urls", {})
        return data
