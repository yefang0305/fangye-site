from __future__ import annotations

import http.cookiejar
import logging
from pathlib import Path

import requests

from . import extract_sec_uid, is_douyin_url, parse_post_list

logger = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)

API_URL = "https://www.douyin.com/aweme/v1/web/aweme/post/"


class ProfileExtractionError(Exception):
    """抖音主页链接提取错误。"""


def _build_api_url(sec_uid: str, cursor: int, count: int) -> str:
    args = (
        "device_platform=webapp&aid=6383&channel=channel_pc_web"
        f"&sec_user_id={sec_uid}&publish_video_strategy_type=2"
        f"&version_code=290100&version_name=29.1.0&count={count}"
        f"&max_cursor={cursor}"
    )
    return f"{API_URL}?{args}"


def _load_cookies(session: requests.Session, cookie_text: str = "", cookie_file: str = "") -> None:
    """从文本或Netscape格式文件加载cookie到session。"""
    if cookie_file:
        cf = Path(cookie_file)
        if cf.exists():
            jar = http.cookiejar.MozillaCookieJar(str(cf))
            jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies.update(jar)
            logger.info("从文件加载 cookies: %s", cf)

    if cookie_text:
        for line in cookie_text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                domain, _, path, secure, expires, name, value = parts[:7]
                session.cookies.set(
                    name, value,
                    domain=domain,
                    path=path,
                    secure=(secure == "TRUE"),
                    expires=int(expires) if expires else None,
                )
        logger.info("从文本加载 cookies (%d 行)", len(cookie_text.strip().splitlines()))


def extract_profile_links(
    profile_url: str,
    cookie_text: str = "",
    cookie_file: str = "",
    timeout: int = 30,
    page_size: int = 35,
    max_pages: int = 200,
) -> dict:
    """从抖音主页提取所有作品链接。

    Returns:
        dict with keys: profile_url, final_url, sec_uid, links, total
    """
    if not is_douyin_url(profile_url):
        raise ProfileExtractionError("仅支持抖音个人主页链接 (douyin.com)")

    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_UA})
    _load_cookies(session, cookie_text=cookie_text, cookie_file=cookie_file)

    redirect = session.get(profile_url, allow_redirects=True, timeout=timeout)
    redirect.raise_for_status()
    final_url = redirect.url
    sec_uid = extract_sec_uid(final_url)
    if not sec_uid:
        raise ProfileExtractionError(f"未能从抖音主页解析 sec_uid: {final_url}")
    referer = f"https://www.douyin.com/user/{sec_uid}"

    seen: set[str] = set()
    links: list[str] = []
    cursor = 0

    for page_num in range(max_pages):
        api_url = _build_api_url(sec_uid, cursor, page_size)
        headers = {
            "User-Agent": DEFAULT_UA,
            "Referer": referer,
            "Accept": "application/json, text/plain, */*",
        }
        resp = session.get(api_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        parsed = parse_post_list(data)
        for link in parsed["links"]:
            if link not in seen:
                seen.add(link)
                links.append(link)

        if not parsed["has_more"]:
            logger.info("已获取全部作品,共 %d 页", page_num + 1)
            break

        next_cursor = int(parsed["max_cursor"] or 0)
        if next_cursor == cursor:
            break
        cursor = next_cursor

    return {
        "profile_url": profile_url,
        "final_url": final_url,
        "sec_uid": sec_uid,
        "links": links,
        "total": len(links),
    }
