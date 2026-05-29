"""Non-network tests for URL parsing, deduplication, report generation,
and downloader option construction."""

import json
import os
import tempfile
from pathlib import Path

from downloader import YtDlpDownloader, DownloadError
from douyin_cr import normalize_crck_cookie_output, parse_aweme_detail
from report import RunReport
from url_utils import (
    extract_video_id,
    is_douyin_url,
    normalize_url,
    safe_filename,
    stable_url_hash,
    validate_urls,
)


# ── URL utilities ──────────────────────────────────────────────────────────

class TestNormalizeUrl:
    def test_strips_trailing_punctuation(self):
        assert normalize_url("https://v.douyin.com/abc/).") == "https://v.douyin.com/abc/"

    def test_unescapes_backslash(self):
        assert normalize_url(r"https://v\.douyin\.com/abc/") == "https://v.douyin.com/abc/"

    def test_preserves_valid_url(self):
        url = "https://www.douyin.com/video/1234567890123456789"
        assert normalize_url(url) == url


class TestStableUrlHash:
    def test_same_url_same_hash(self):
        a = stable_url_hash("https://v.douyin.com/abc/")
        b = stable_url_hash("https://v.douyin.com/abc/")
        assert a == b

    def test_different_url_different_hash(self):
        a = stable_url_hash("https://v.douyin.com/abc/")
        b = stable_url_hash("https://v.douyin.com/def/")
        assert a != b

    def test_hash_length(self):
        h = stable_url_hash("https://www.douyin.com/video/123")
        assert len(h) == 16


class TestSafeFilename:
    def test_replaces_unsafe_chars(self):
        assert safe_filename('a<b>c:"d/e\\f|g?h*i') == "a_b_c__d_e_f_g_h_i"

    def test_truncates_long_name(self):
        long_name = "a" * 200
        result = safe_filename(long_name)
        assert len(result) <= 120

    def test_fallback_for_empty(self):
        assert safe_filename("<>:\"") == "untitled"


class TestIsDouyinUrl:
    def test_video_url(self):
        assert is_douyin_url("https://www.douyin.com/video/1234567890123456789")

    def test_note_url(self):
        assert is_douyin_url("https://www.douyin.com/note/9876543210987654321")

    def test_short_link(self):
        assert is_douyin_url("https://v.douyin.com/AbCdEfG/")

    def test_non_douyin_url(self):
        assert not is_douyin_url("https://www.bilibili.com/video/BV12345678")

    def test_empty_string(self):
        assert not is_douyin_url("")

    def test_not_http(self):
        assert not is_douyin_url("not a url")


class TestExtractVideoId:
    def test_video_path(self):
        assert extract_video_id("https://www.douyin.com/video/1234567890123456789") == "1234567890123456789"

    def test_note_path(self):
        assert extract_video_id("https://www.douyin.com/note/9876543210987654321") == "9876543210987654321"

    def test_no_id(self):
        assert extract_video_id("https://v.douyin.com/AbCdEfG/") == ""

    def test_trailing_slash(self):
        assert extract_video_id("https://www.douyin.com/video/12345/") == "12345"


class TestValidateUrls:
    def test_valid_urls(self):
        raw = "https://www.douyin.com/video/123\nhttps://v.douyin.com/abc/"
        valid, rejected = validate_urls(raw)
        assert len(valid) == 2
        assert len(rejected) == 0

    def test_rejects_non_douyin(self):
        raw = "https://www.bilibili.com/video/BV123"
        valid, rejected = validate_urls(raw)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_rejects_non_http(self):
        raw = "just some text"
        valid, rejected = validate_urls(raw)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_skips_empty_lines_and_comments(self):
        raw = "\n# this is a comment\nhttps://www.douyin.com/video/123\n\n"
        valid, rejected = validate_urls(raw)
        assert len(valid) == 1
        assert len(rejected) == 0

    def test_deduplicates(self):
        raw = "https://www.douyin.com/video/123\nhttps://www.douyin.com/video/123"
        valid, rejected = validate_urls(raw)
        assert len(valid) == 1

    def test_deduplicates_with_trailing_punctuation(self):
        raw = "https://v.douyin.com/abc/).\nhttps://v.douyin.com/abc/"
        valid, rejected = validate_urls(raw)
        assert len(valid) == 1


# ── Report ─────────────────────────────────────────────────────────────────

class TestRunReport:
    def test_empty_report(self):
        r = RunReport()
        r.finish()
        assert r.summary == {"total": 0, "ok": 0, "fail": 0, "skipped": 0}

    def test_mixed_entries(self):
        r = RunReport()
        r.record("https://a.douyin.com/1", "ok", "done", "/tmp/a.mp4")
        r.record("https://a.douyin.com/2", "fail", "timeout")
        r.record("https://a.douyin.com/3", "skipped", "not douyin")
        r.finish()
        assert r.summary == {"total": 3, "ok": 1, "fail": 1, "skipped": 1}

    def test_markdown_has_headings(self):
        r = RunReport()
        r.record("https://a.douyin.com/1", "ok")
        r.finish()
        md = r.to_markdown()
        assert "# 抖音视频下载报告" in md
        assert "https://a.douyin.com/1" in md

    def test_json_is_valid(self):
        r = RunReport()
        r.record("https://a.douyin.com/1", "ok")
        r.finish()
        obj = json.loads(r.to_json())
        assert obj["summary"]["total"] == 1
        assert obj["entries"][0]["url"] == "https://a.douyin.com/1"

    def test_save_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = RunReport()
            r.record("https://a.douyin.com/1", "ok")
            r.finish()
            md_path, json_path = r.save(tmp)
            assert md_path.exists()
            assert json_path.exists()
            assert md_path.suffix == ".md"
            assert json_path.suffix == ".json"


# ── Downloader option construction ─────────────────────────────────────────

class TestDownloaderOptions:
    def test_default_opts(self):
        d = YtDlpDownloader()
        opts = d._build_opts("test_out/%(title)s-%(id)s.%(ext)s")
        assert opts["format"] == "bv*+ba/best"
        assert "cookiefile" not in opts
        assert "cookiesfrombrowser" not in opts

    def test_cookie_file_opts(self):
        d = YtDlpDownloader(cookie_file="/tmp/cookies.txt")
        opts = d._build_opts("out")
        assert opts["cookiefile"] == "/tmp/cookies.txt"

    def test_cookies_from_browser_opts(self):
        d = YtDlpDownloader(cookies_from_browser="chrome")
        opts = d._build_opts("out")
        assert opts["cookiesfrombrowser"] == ("chrome",)

    def test_crtubeget_enabled(self):
        d = YtDlpDownloader(crtubeget_dir="C:/CRTubeGet")
        assert d._should_use_crtubeget_first("https://www.douyin.com/video/123")

    def test_crtubeget_disabled_without_dir(self):
        d = YtDlpDownloader()
        assert not d._should_use_crtubeget_first("https://www.douyin.com/video/123")

    def test_crtubeget_fallback_on_fresh_cookie_error(self):
        d = YtDlpDownloader(crtubeget_dir="C:/CRTubeGet", prefer_crtubeget=False)
        assert d._can_fallback_to_crtubeget("https://www.douyin.com/video/123", "Fresh cookies required")


class TestDouyinCR:
    def test_normalize_crck_cookie_output(self):
        raw = "Cookie: # Netscape HTTP Cookie File\n.douyin.com\tTRUE\t/\tFALSE\t0\ttest\tvalue\n"
        normalized = normalize_crck_cookie_output(raw)
        assert normalized.startswith("# Netscape HTTP Cookie File")
        assert ".douyin.com" in normalized

    def test_parse_aweme_detail(self):
        data = {
            "aweme_detail": {
                "aweme_id": "123",
                "desc": "测试视频",
                "duration": 5000,
                "video": {
                    "height": 1080,
                    "play_addr": {
                        "uri": "video_uri",
                        "url_list": ["https://example.com/playwm"]
                    },
                    "cover": {"url_list": ["https://example.com/cover.jpg"]},
                },
            }
        }
        parsed = parse_aweme_detail(data, "https://www.douyin.com/video/123")
        assert parsed["id"] == "123"
        assert parsed["title"] == "测试视频"
        assert parsed["duration"] == 5
        assert parsed["direct_url"].startswith("https://aweme.snssdk.com/aweme/v1/play/")
        assert parsed["thumbnail"] == "https://example.com/cover.jpg"


# ── Download error helper ──────────────────────────────────────────────────

class TestDownloadError:
    def test_is_runtime_error(self):
        err = DownloadError("test")
        assert isinstance(err, RuntimeError)


def _run_tests() -> int:
    total = 0
    failed = 0
    for obj in list(globals().values()):
        if not isinstance(obj, type) or not obj.__name__.startswith("Test"):
            continue
        instance = obj()
        for name in sorted(dir(instance)):
            if not name.startswith("test_"):
                continue
            total += 1
            try:
                getattr(instance, name)()
                print(f"PASS {obj.__name__}.{name}")
            except Exception as exc:
                failed += 1
                print(f"FAIL {obj.__name__}.{name}: {type(exc).__name__}: {exc}")
    print(f"\n{total - failed}/{total} tests passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_tests())
