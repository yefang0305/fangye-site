from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import extract_sec_uid, is_douyin_url, parse_post_list
from core.markdown_exporter import export_links_to_markdown, safe_filename


def run_tests():
    errors = []

    def check(condition, name):
        if not condition:
            errors.append(f"FAIL: {name}")
        else:
            print(f"  PASS: {name}")

    print("extract_sec_uid")
    check(extract_sec_uid("https://www.douyin.com/user/MS4wLjABxxxx") == "MS4wLjABxxxx", "path based")
    check(extract_sec_uid("https://www.douyin.com/user/x?sec_uid=abc") == "abc", "sec_uid param")
    check(extract_sec_uid("https://www.douyin.com/user/x?sec_user_id=xyz") == "xyz", "sec_user_id param")
    check(extract_sec_uid("https://www.douyin.com/") == "", "no uid")
    check(extract_sec_uid("https://v.douyin.com/abc/") == "", "short link")

    print("is_douyin_url")
    check(is_douyin_url("https://www.douyin.com/user/test") is True, "douyin main")
    check(is_douyin_url("https://v.douyin.com/abc/") is True, "short link")
    check(is_douyin_url("https://www.bilibili.com/") is False, "not douyin")

    print("parse_post_list")
    r = parse_post_list({
        "aweme_list": [{"aweme_id": "123"}, {"aweme_id": "456"}],
        "has_more": True,
        "max_cursor": 10,
    })
    check(len(r["links"]) == 2, "aweme_list count")
    check(r["links"][0] == "https://www.douyin.com/video/123", "link format")
    check(r["has_more"] is True, "has_more")
    check(r["max_cursor"] == 10, "max_cursor")

    r2 = parse_post_list({
        "awemeList": [{"id": "789"}],
        "hasMore": False,
        "maxCursor": 0,
    })
    check(len(r2["links"]) == 1, "awemeList count")
    check(r2["has_more"] is False, "hasMore false")

    r3 = parse_post_list({})
    check(r3["links"] == [], "empty input")

    print("safe_filename")
    check(safe_filename("hello") == "hello", "normal")
    check("<" not in safe_filename('bad<name>'), "strip invalid chars")
    check(safe_filename("  .  ", "fb") == "fb", "fallback")

    print("export_links_to_markdown")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = export_links_to_markdown(
            "https://www.douyin.com/user/test", "sec123",
            ["https://www.douyin.com/video/1", "https://www.douyin.com/video/2"],
            tmp,
        )
        check(path.exists(), "file created")
        content = path.read_text(encoding="utf-8")
        check("抖音主页作品链接" in content, "has title")
        check("sec123" in content, "has sec_uid")
        check("作品数量" in content and "2" in content, "has count")
        check("https://www.douyin.com/video/1" in content, "has link 1")
        check("https://www.douyin.com/video/2" in content, "has link 2")

    if errors:
        print(f"\n{len(errors)} FAILURES:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\nAll tests passed!")


if __name__ == "__main__":
    run_tests()
