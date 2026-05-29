"""Douyin URL validation, parsing, and deduplication utilities."""

import hashlib
import re
from urllib.parse import urlparse


DOUYIN_PATTERNS = [
    re.compile(r"https?://(?:www\.)?douyin\.com/(?:video|note)/(\d+)", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?douyin\.com/user/([\w.-]+)", re.IGNORECASE),
    re.compile(r"https?://v\.douyin\.com/([^/?#]+)", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?iesdouyin\.com/", re.IGNORECASE),
]


def normalize_url(url: str) -> str:
    """Strip trailing punctuation and unescape backslash-escaped characters."""
    normalized = url.strip().rstrip(").,，。；;")
    for ch in ("_", "-", ".", "(", ")", "[", "]"):
        normalized = normalized.replace(f"\\{ch}", ch)
    return normalized


def stable_url_hash(url: str) -> str:
    """SHA-256 hex digest of a normalized URL, truncated to 16 chars."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def safe_filename(value: str, fallback: str = "untitled") -> str:
    """Replace filesystem-unsafe characters and truncate to 120 chars."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" ._")
    return cleaned[:120] or fallback


def is_douyin_url(url: str) -> bool:
    """Return True if url looks like a Douyin video or user link."""
    host = urlparse(url).netloc.lower()
    if "douyin.com" not in host and "iesdouyin.com" not in host:
        return False
    for pattern in DOUYIN_PATTERNS:
        if pattern.search(url):
            return True
    return False


def extract_video_id(url: str) -> str:
    """Extract the numeric video ID from a Douyin /video/ or /note/ URL, or ''."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    for marker in ("video", "note"):
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    return ""


def validate_urls(raw_text: str) -> tuple[list[str], list[str]]:
    """Split raw text into lines, filter empty/comment lines, return (valid, rejected)."""
    valid: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        normalized = normalize_url(line)
        if not normalized.startswith("http"):
            rejected.append(line)
            continue
        if not is_douyin_url(normalized):
            rejected.append(line)
            continue
        key = normalized
        if key in seen:
            continue
        seen.add(key)
        valid.append(normalized)
    return valid, rejected
