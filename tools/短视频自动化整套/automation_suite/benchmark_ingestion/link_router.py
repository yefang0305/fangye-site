from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .models import normalize_url


class LinkType(str, Enum):
    SINGLE = "single"
    ACCOUNT = "account"
    COLLECTION = "collection"
    PLAYLIST = "playlist"
    LIVE = "live"
    SHORTLINK = "shortlink"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LinkRecognition:
    url: str
    platform: str
    link_type: LinkType
    reason: str


RULES: list[tuple[str, LinkType, str, str]] = [
    ("douyin", LinkType.SHORTLINK, r"https?://v\.douyin\.com/[^/?#]+", "douyin short link"),
    ("douyin", LinkType.SINGLE, r"douyin\.com/(?:video|note)/\d+", "douyin single video"),
    ("douyin", LinkType.ACCOUNT, r"douyin\.com/user/[\w.-]+", "douyin account"),
    ("douyin", LinkType.COLLECTION, r"douyin\.com/collection/\d+", "douyin collection"),
    ("bilibili", LinkType.SINGLE, r"bilibili\.com/video/(?:BV\w+|av\d+)", "bilibili single video"),
    ("bilibili", LinkType.COLLECTION, r"bilibili\.com/.+collectiondetail\?sid=\d+", "bilibili collection"),
    ("bilibili", LinkType.ACCOUNT, r"space\.bilibili\.com/\d+", "bilibili account"),
    ("youtube", LinkType.SINGLE, r"(?:youtube\.com/watch\?v=|youtube\.com/shorts/|youtu\.be/)[\w-]+", "youtube single video"),
    ("youtube", LinkType.PLAYLIST, r"youtube\.com/playlist\?list=[\w-]+", "youtube playlist"),
    ("youtube", LinkType.ACCOUNT, r"youtube\.com/(?:channel/|@)[\w.-]+", "youtube channel"),
    ("xiaohongshu", LinkType.SINGLE, r"xiaohongshu\.com/explore/[\w.-]+", "xiaohongshu note"),
    ("xiaohongshu", LinkType.ACCOUNT, r"xiaohongshu\.com/user/profile/[\w.-]+", "xiaohongshu account"),
    ("kuaishou", LinkType.SINGLE, r"kuaishou\.com/short-video/[\w.-]+", "kuaishou video"),
    ("kuaishou", LinkType.ACCOUNT, r"kuaishou\.com/profile/[\w.-]+", "kuaishou account"),
]


def recognize_url(url: str) -> LinkRecognition:
    """Recognize a video platform URL and classify its type."""
    normalized = normalize_url(url)
    for platform, link_type, pattern, reason in RULES:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return LinkRecognition(normalized, platform, link_type, reason)
    return LinkRecognition(normalized, "unknown", LinkType.UNKNOWN, "no rule matched")
