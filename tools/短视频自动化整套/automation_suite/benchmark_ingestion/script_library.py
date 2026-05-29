from __future__ import annotations

from pathlib import Path
import json

from .models import ScriptRecord, ensure_parent, now_iso, safe_filename


class ScriptLibrary:
    """Manages cleaned scripts as indexed records with text file storage.

    Scripts are stored as individual .txt files under a 'txt/' subdirectory
    and indexed in a JSON library file. Only metadata is kept in the index;
    raw and cleaned scripts are stored as separate text files.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.text_dir = self.path.parent / "txt"
        self._data = self._load()

    def add_script(
        self,
        source_url: str,
        raw_script: str,
        cleaned_script: str,
        video_path: str = "",
        title: str = "",
        meta: dict | None = None,
    ) -> dict:
        full_record = ScriptRecord(
            source_url=source_url,
            raw_script=raw_script.strip(),
            cleaned_script=cleaned_script.strip(),
            video_path=video_path,
            title=title,
            meta=meta or {},
        ).to_dict()
        script_path = self._write_script_text(full_record)
        record = self._to_index_record(full_record, script_path)
        self._data["scripts"].append(record)
        self.save()
        return self._hydrate_record(record)

    def list_scripts(self, status: str | None = None) -> list[dict]:
        scripts = list(self._data["scripts"])
        if status:
            scripts = [item for item in scripts if item.get("status") == status]
        return [self._hydrate_record(item) for item in scripts]

    def mark_used(self, script_id: str) -> bool:
        for record in self._data["scripts"]:
            if record.get("id") == script_id:
                record["status"] = "used"
                record["used_at"] = now_iso()
                self.save()
                return True
        return False

    def save(self) -> None:
        ensure_parent(self.path)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> dict:
        if not self.path.exists():
            return {"schema_version": 1, "scripts": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"schema_version": 1, "scripts": []}
        if not isinstance(data, dict):
            return {"schema_version": 1, "scripts": []}
        data.setdefault("schema_version", 1)
        data.setdefault("scripts", [])
        return data

    def _write_script_text(self, record: dict) -> str:
        self.text_dir.mkdir(parents=True, exist_ok=True)
        name_seed = record.get("title") or record.get("cleaned_script", "")[:24]
        filename = f"{record['id']}_{safe_filename(name_seed, 'script')}.txt"
        path = self.text_dir / filename
        path.write_text(record.get("cleaned_script", "").strip(), encoding="utf-8")
        return str(path)

    def _to_index_record(self, record: dict, script_path: str) -> dict:
        return {
            "id": record.get("id", ""),
            "source_url": record.get("source_url", ""),
            "script_path": script_path,
            "preview": record.get("cleaned_script", "").replace("\n", " ")[:80],
            "video_path": record.get("video_path", ""),
            "title": record.get("title", ""),
            "status": record.get("status", "ready"),
            "created_at": record.get("created_at", ""),
            "used_at": record.get("used_at", ""),
            "meta": record.get("meta", {}),
        }

    def _hydrate_record(self, record: dict) -> dict:
        hydrated = dict(record)
        if "cleaned_script" not in hydrated:
            hydrated["cleaned_script"] = self._read_script_text(record.get("script_path", ""))
        hydrated.setdefault("raw_script", "")
        return hydrated

    def _read_script_text(self, script_path: str) -> str:
        if not script_path:
            return ""
        path = Path(script_path)
        try:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
        return ""
