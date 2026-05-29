from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def extract_sec_uid(url: str) -> str:
    """从抖音个人主页URL中提取 sec_uid。"""
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
    """解析抖音作品列表API响应,提取作品链接和分页信息。"""
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


def is_douyin_url(url: str) -> bool:
    """判断是否为抖音链接。"""
    host = urlparse(url).netloc.lower()
    return "douyin.com" in host or "iesdouyin.com" in host
