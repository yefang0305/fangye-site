from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import extract_sec_uid, is_douyin_url, parse_post_list
from core.markdown_exporter import export_links_to_markdown, safe_filename


class TestExtractSecUid:
    def test_query_param_sec_uid(self):
        url = "https://www.douyin.com/user/MS4wLjABAAAAxxx?sec_uid=MS4wLjABAAAAabc123"
        assert extract_sec_uid(url) == "MS4wLjABAAAAabc123"

    def test_query_param_sec_user_id(self):
        url = "https://www.douyin.com/user/test?sec_user_id=MS4wLjABAAAAxyz"
        assert extract_sec_uid(url) == "MS4wLjABAAAAxyz"

    def test_path_based(self):
        url = "https://www.douyin.com/user/MS4wLjABAAAAdef456"
        assert extract_sec_uid(url) == "MS4wLjABAAAAdef456"

    def test_no_sec_uid(self):
        assert extract_sec_uid("https://www.douyin.com/") == ""

    def test_short_link(self):
        assert extract_sec_uid("https://v.douyin.com/abc123/") == ""


class TestIsDouyinUrl:
    def test_main_domain(self):
        assert is_douyin_url("https://www.douyin.com/user/test")

    def test_short_link(self):
        assert is_douyin_url("https://v.douyin.com/abc123/")

    def test_not_douyin(self):
        assert not is_douyin_url("https://www.bilibili.com/video/BV123")
        assert not is_douyin_url("https://www.youtube.com/watch?v=abc")


class TestParsePostList:
    def test_with_aweme_list(self):
        data = {
            "aweme_list": [
                {"aweme_id": "123456"},
                {"aweme_id": "789012"},
            ],
            "has_more": True,
            "max_cursor": 20,
        }
        result = parse_post_list(data)
        assert len(result["links"]) == 2
        assert result["links"][0] == "https://www.douyin.com/video/123456"
        assert result["links"][1] == "https://www.douyin.com/video/789012"
        assert result["has_more"] is True
        assert result["max_cursor"] == 20

    def test_with_awemeList(self):
        data = {
            "awemeList": [
                {"id": "111"},
                {"aweme_id": "222"},
            ],
            "hasMore": False,
            "maxCursor": 0,
        }
        result = parse_post_list(data)
        assert len(result["links"]) == 2
        assert result["has_more"] is False
        assert result["max_cursor"] == 0

    def test_empty(self):
        result = parse_post_list({})
        assert result["links"] == []
        assert result["has_more"] is False
        assert result["max_cursor"] == 0

    def test_missing_id(self):
        data = {"aweme_list": [{"desc": "no id field"}]}
        result = parse_post_list(data)
        assert result["links"] == []

    def test_deduplication(self):
        """parse_post_list 不负责去重,调用方负责。此处验证返回顺序。"""
        data = {"aweme_list": [{"aweme_id": "333"}, {"aweme_id": "333"}]}
        result = parse_post_list(data)
        assert len(result["links"]) == 2  # raw extraction, no dedup


class TestSafeFilename:
    def test_normal(self):
        assert safe_filename("hello") == "hello"

    def test_invalid_chars(self):
        name = safe_filename('file<name>:with"bad?chars*')
        assert "<" not in name
        assert ">" not in name
        assert ":" not in name
        assert '"' not in name
        assert "?" not in name
        assert "*" not in name

    def test_fallback(self):
        assert safe_filename("   . ", "untitled") == "untitled"

    def test_truncation(self):
        long_name = "a" * 200
        assert len(safe_filename(long_name)) <= 120


class TestExportLinksToMarkdown:
    def test_export_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = export_links_to_markdown(
                profile_url="https://www.douyin.com/user/test",
                sec_uid="MS4wLjABxxx",
                links=["https://www.douyin.com/video/111", "https://www.douyin.com/video/222"],
                output_dir=tmp,
            )
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "抖音主页作品链接" in content
            assert "https://www.douyin.com/user/test" in content
            assert "MS4wLjABxxx" in content
            assert "作品数量" in content and "2" in content
            assert "https://www.douyin.com/video/111" in content
            assert "https://www.douyin.com/video/222" in content

    def test_empty_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = export_links_to_markdown(
                profile_url="https://www.douyin.com/user/test",
                sec_uid="MS4wLjABxxx",
                links=[],
                output_dir=tmp,
            )
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "作品数量" in content and "0" in content


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
