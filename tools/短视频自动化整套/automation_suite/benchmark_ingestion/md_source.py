from __future__ import annotations

from pathlib import Path
import re

from .models import normalize_url


URL_RE = re.compile(r"https?://[^\s<>\]\)\"']+", re.IGNORECASE)
RESULT_RE = re.compile(r"<!--\s*video_tool:(?:processed|rejected)\b.*?-->", re.IGNORECASE)
LINK_MARKER_RE = re.compile(r"<!--\s*video_tool:(?:processed|rejected|expanded)\b.*?-->", re.IGNORECASE)


def extract_video_links(text: str) -> list[str]:
    """Extract unique video platform URLs from text."""
    seen: set[str] = set()
    links: list[str] = []
    for match in URL_RE.finditer(text or ""):
        url = normalize_url(match.group(0))
        if not _looks_like_video_url(url):
            continue
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        links.append(url)
    return links


def read_links_from_md(path: str | Path) -> list[str]:
    """Read video links from a markdown file, skipping already-marked ones."""
    source = Path(path)
    if not source.exists():
        return []
    return extract_unmarked_video_links(source.read_text(encoding="utf-8"))


def extract_unmarked_video_links(text: str) -> list[str]:
    """Extract video links that have not been marked as processed/rejected."""
    lines = (text or "").splitlines()
    seen: set[str] = set()
    links: list[str] = []
    for index, line in enumerate(lines):
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if LINK_MARKER_RE.fullmatch(next_line):
            continue
        for match in URL_RE.finditer(line):
            url = normalize_url(match.group(0))
            if not _looks_like_video_url(url):
                continue
            key = url.lower()
            if key in seen:
                continue
            seen.add(key)
            links.append(url)
    return links


def mark_processed_link(text: str, url: str, timestamp: str) -> str:
    return _mark_link(text, url, f"<!-- video_tool:processed {timestamp} -->")


def mark_rejected_link(text: str, url: str, timestamp: str, reason: str = "") -> str:
    escaped_reason = (reason or "").replace('"', "'").strip()
    marker = f"<!-- video_tool:rejected {timestamp} reason=\"{escaped_reason}\" -->"
    return _mark_link(text, url, marker)


def append_expanded_links(
    text: str,
    profile_url: str,
    video_links: list[str],
    timestamp: str,
    profile_title: str = "",
) -> str:
    """Append expanded profile links to markdown text with markers."""
    existing = {normalize_url(url).lower() for url in extract_video_links(text)}
    new_links = []
    for link in video_links:
        normalized = normalize_url(link)
        key = normalized.lower()
        if key in existing:
            continue
        existing.add(key)
        new_links.append(normalized)
    if not new_links:
        return text

    marker = f"<!-- video_tool:expanded {timestamp} count={len(new_links)} -->"
    marked_text = _mark_link(text, profile_url, marker, marker_re=LINK_MARKER_RE)
    title = (profile_title or "抖音账号").strip()
    block = [
        "",
        f"## 展开自主页：{title}",
        "",
        *new_links,
        "",
    ]
    source = marked_text.rstrip()
    return source + "\n" + "\n".join(block)


def append_expanded_links_file(
    path: str | Path,
    profile_url: str,
    video_links: list[str],
    timestamp: str,
    profile_title: str = "",
) -> int:
    """Update a markdown file with expanded profile links. Returns count of new links."""
    source = Path(path)
    original = source.read_text(encoding="utf-8") if source.exists() else ""
    updated = append_expanded_links(original, profile_url, video_links, timestamp, profile_title)
    if updated == original:
        return 0
    source.write_text(updated, encoding="utf-8")
    return max(0, len(extract_video_links(updated)) - len(extract_video_links(original)))


def mark_rejected_file(path: str | Path, url: str, timestamp: str, reason: str = "") -> bool:
    source = Path(path)
    if not source.exists():
        return False
    original = source.read_text(encoding="utf-8")
    updated = mark_rejected_link(original, url, timestamp, reason)
    if updated == original:
        return False
    source.write_text(updated, encoding="utf-8")
    return True


def _mark_link(text: str, url: str, marker: str, marker_re=RESULT_RE) -> str:
    lines = text.splitlines()
    normalized = normalize_url(url)
    out: list[str] = []
    marked = False

    for index, line in enumerate(lines):
        out.append(line)
        if marked or normalized not in line:
            continue
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if marker_re.fullmatch(next_line):
            marked = True
            continue
        out.append(marker)
        marked = True

    if not marked:
        out.append(normalized)
        out.append(marker)

    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(out) + suffix


def mark_processed_file(path: str | Path, url: str, timestamp: str) -> bool:
    source = Path(path)
    if not source.exists():
        return False
    original = source.read_text(encoding="utf-8")
    updated = mark_processed_link(original, url, timestamp)
    if updated == original:
        return False
    source.write_text(updated, encoding="utf-8")
    return True


def _looks_like_video_url(url: str) -> bool:
    lowered = url.lower()
    domains = (
        "douyin.com",
        "iesdouyin.com",
        "bilibili.com",
        "b23.tv",
        "youtube.com",
        "youtu.be",
        "xiaohongshu.com",
        "xhslink.com",
        "kuaishou.com",
        "gifshow.com",
    )
    return any(domain in lowered for domain in domains)
