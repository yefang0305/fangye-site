from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import hashlib
import re
import uuid


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stable_url_hash(url: str) -> str:
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def normalize_url(url: str) -> str:
    normalized = url.strip().rstrip(").,，。；;")
    for escaped in ("_", "-", ".", "(", ")", "[", "]"):
        normalized = normalized.replace(f"\\{escaped}", escaped)
    return normalized


def safe_filename(value: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" ._")
    return cleaned[:120] or fallback


@dataclass
class ProcessResult:
    url: str
    status: str
    message: str = ""
    video_path: str = ""
    script_id: str = ""


@dataclass
class ScriptRecord:
    source_url: str
    raw_script: str
    cleaned_script: str
    video_path: str = ""
    title: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    status: str = "ready"
    created_at: str = field(default_factory=now_iso)
    used_at: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_url": self.source_url,
            "raw_script": self.raw_script,
            "cleaned_script": self.cleaned_script,
            "video_path": self.video_path,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "used_at": self.used_at,
            "meta": self.meta,
        }


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
