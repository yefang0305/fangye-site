from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import tempfile

import requests

from .douyin_cr import DEFAULT_UA, DouyinCRResolver, is_douyin_url
from .downloader import DownloadError


@dataclass
class DouyinProfileExpansion:
    profile_url: str
    final_url: str
    sec_uid: str
    title: str = "抖音账号"
    links: list[str] = field(default_factory=list)


def extract_sec_uid(url: str) -> str:
    """Extract sec_uid from a 抖音 profile URL."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("sec_uid", "sec_user_id"):
        value = query.get(key, [""])[0]
        if value:
            return value

    parts = [part for part in parsed.path.split("/") if part]
    if "user" in parts:
        index = parts.index("user")
        if index + 1 < len(parts):
            return parts[index + 1]
    return ""


def parse_post_list(data: dict) -> dict:
    """Parse 抖音 post list API response into video links."""
    items = data.get("aweme_list") or data.get("awemeList") or []
    links: list[str] = []
    for item in items:
        aweme_id = str(item.get("aweme_id") or item.get("id") or "").strip()
        if aweme_id:
            links.append(f"https://www.douyin.com/video/{aweme_id}")
    return {
        "links": links,
        "has_more": bool(data.get("has_more") or data.get("hasMore")),
        "max_cursor": data.get("max_cursor") or data.get("maxCursor") or 0,
    }


class DouyinProfileExpander:
    """Expand a 抖音 profile URL into all its published video links.

    Requires CR TubeGet installed for cookie management and session
    initialization. Fetches paginated post lists via the aweme/post API.
    """

    def __init__(
        self,
        crtubeget_dir: str | Path,
        cookie_file: str = "",
        timeout: int = 30,
        page_size: int = 35,
        max_pages: int = 200,
    ):
        self.resolver = DouyinCRResolver(crtubeget_dir, cookie_file=cookie_file, timeout=timeout)
        self.timeout = timeout
        self.page_size = page_size
        self.max_pages = max_pages

    def expand(self, url: str) -> DouyinProfileExpansion:
        if not is_douyin_url(url):
            raise DownloadError("抖音主页展开仅支持抖音链接")

        with tempfile.TemporaryDirectory(prefix="douyin_profile_") as tmp:
            tmp_path = Path(tmp)
            session = requests.Session()
            session.headers.update({"User-Agent": DEFAULT_UA})
            self.resolver._load_cookies(session, url, tmp_path)

            redirect = session.get(url, allow_redirects=True, timeout=self.timeout)
            redirect.raise_for_status()
            final_url = redirect.url
            sec_uid = extract_sec_uid(final_url)
            if not sec_uid:
                raise DownloadError(f"未能从抖音主页解析 sec_uid: {final_url}")
            referer = f"https://www.douyin.com/user/{sec_uid}"

            links = self._fetch_all_links(session, sec_uid, referer, tmp_path)
            if not links:
                raise DownloadError("抖音主页未返回作品链接")
            return DouyinProfileExpansion(
                profile_url=url,
                final_url=final_url,
                sec_uid=sec_uid,
                links=links,
            )

    def _fetch_all_links(
        self,
        session: requests.Session,
        sec_uid: str,
        referer: str,
        tmp_path: Path,
    ) -> list[str]:
        seen: set[str] = set()
        links: list[str] = []
        cursor = 0
        for _ in range(self.max_pages):
            page = self._fetch_page(session, sec_uid, cursor, referer, tmp_path)
            parsed = parse_post_list(page)
            for link in parsed["links"]:
                if link in seen:
                    continue
                seen.add(link)
                links.append(link)
            if not parsed["has_more"]:
                break
            next_cursor = int(parsed["max_cursor"] or 0)
            if next_cursor == cursor:
                break
            cursor = next_cursor
        return links

    def _fetch_page(
        self,
        session: requests.Session,
        sec_uid: str,
        cursor: int,
        referer: str,
        tmp_path: Path,
    ) -> dict:
        args = (
            "device_platform=webapp&aid=6383&channel=channel_pc_web"
            f"&sec_user_id={sec_uid}&publish_video_strategy_type=2"
            f"&version_code=290100&version_name=29.1.0&count={self.page_size}"
            f"&max_cursor={cursor}"
        )
        api_url = f"https://www.douyin.com/aweme/v1/web/aweme/post/?{args}"
        headers = {
            "User-Agent": DEFAULT_UA,
            "Referer": referer,
            "Accept": "application/json, text/plain, */*",
        }
        response = session.get(api_url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
