import json
import tempfile
import unittest
from pathlib import Path


class MarkdownSourceTests(unittest.TestCase):
    def test_extract_links_dedupes_and_keeps_order(self):
        from automation_suite.benchmark_ingestion.md_source import extract_video_links

        text = """
        https://v.douyin.com/abc123
        - [same](https://v.douyin.com/abc123)
        https://www.douyin.com/video/731234567890
        not-a-link
        https://space.bilibili.com/123456
        """

        self.assertEqual(
            extract_video_links(text),
            [
                "https://v.douyin.com/abc123",
                "https://www.douyin.com/video/731234567890",
                "https://space.bilibili.com/123456",
            ],
        )

    def test_extract_links_unescapes_markdown_shortlink_underscores(self):
        from automation_suite.benchmark_ingestion.md_source import extract_video_links

        text = r"https://v.douyin.com/\_yUlpQI4RmM/"

        self.assertEqual(extract_video_links(text), ["https://v.douyin.com/_yUlpQI4RmM/"])

    def test_mark_processed_appends_html_comment_once(self):
        from automation_suite.benchmark_ingestion.md_source import mark_processed_link

        text = "https://v.douyin.com/abc123\n"
        marked = mark_processed_link(text, "https://v.douyin.com/abc123", "2026-05-08T00:00:00")
        marked_again = mark_processed_link(marked, "https://v.douyin.com/abc123", "2026-05-08T00:00:00")

        self.assertIn("<!-- video_tool:processed 2026-05-08T00:00:00 -->", marked)
        self.assertEqual(marked, marked_again)

    def test_append_expanded_links_adds_profile_section_without_duplicates(self):
        from automation_suite.benchmark_ingestion.md_source import append_expanded_links

        text = "https://v.douyin.com/profile123/\nhttps://www.douyin.com/video/1\n"
        updated = append_expanded_links(
            text,
            "https://v.douyin.com/profile123/",
            ["https://www.douyin.com/video/1", "https://www.douyin.com/video/2"],
            "2026-05-14T12:00:00",
            "玄学账号",
        )
        updated_again = append_expanded_links(
            updated,
            "https://v.douyin.com/profile123/",
            ["https://www.douyin.com/video/2"],
            "2026-05-14T12:30:00",
            "玄学账号",
        )

        self.assertIn("<!-- video_tool:expanded 2026-05-14T12:00:00 count=1 -->", updated)
        self.assertIn("## 展开自主页：玄学账号", updated)
        self.assertEqual(updated.count("https://www.douyin.com/video/1"), 1)
        self.assertEqual(updated.count("https://www.douyin.com/video/2"), 1)
        self.assertEqual(updated, updated_again)

    def test_append_expanded_links_supports_separate_profile_input(self):
        from automation_suite.benchmark_ingestion.md_source import append_expanded_links

        updated = append_expanded_links(
            "",
            "https://v.douyin.com/profile123/",
            ["https://www.douyin.com/video/1"],
            "2026-05-14T12:00:00",
            "玄学账号",
        )

        self.assertIn("<!-- video_tool:expanded 2026-05-14T12:00:00 count=1 -->", updated)
        self.assertIn("## 展开自主页：玄学账号", updated)
        self.assertIn("https://www.douyin.com/video/1", updated)

    def test_mark_rejected_appends_rejected_comment_once(self):
        from automation_suite.benchmark_ingestion.md_source import mark_rejected_link

        text = "https://www.douyin.com/video/1\n"
        marked = mark_rejected_link(text, "https://www.douyin.com/video/1", "2026-05-14T12:00:00", "女性视角")
        marked_again = mark_rejected_link(marked, "https://www.douyin.com/video/1", "2026-05-14T12:30:00", "女性视角")

        self.assertIn("<!-- video_tool:rejected 2026-05-14T12:00:00 reason=\"女性视角\" -->", marked)
        self.assertEqual(marked, marked_again)


class StateStoreTests(unittest.TestCase):
    def test_state_store_tracks_processed_urls_by_hash(self):
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            store = IngestionStateStore(path)
            self.assertFalse(store.is_processed("https://v.douyin.com/abc123"))
            store.update_url(
                "https://v.douyin.com/abc123",
                status="downloaded",
                video_path="output/douyin_library/a.mp4",
            )
            self.assertFalse(store.is_processed("https://v.douyin.com/abc123"))

            store.update_url(
                "https://v.douyin.com/abc123",
                status="llm_done",
                video_path="output/douyin_library/a.mp4",
                script_id="script-1",
            )

            reloaded = IngestionStateStore(path)
            self.assertTrue(reloaded.is_processed("https://v.douyin.com/abc123"))
            record = reloaded.get_url("https://v.douyin.com/abc123")
            self.assertEqual(record["status"], "llm_done")
            self.assertEqual(record["script_id"], "script-1")

    def test_state_store_treats_permanent_failed_as_processed(self):
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            store = IngestionStateStore(Path(tmp) / "state.json")
            url = "https://v.douyin.com/permanent"

            store.update_url(url, status="permanent_failed", failure_count=3)

            self.assertTrue(store.is_processed(url))


class ScriptLibraryTests(unittest.TestCase):
    def test_script_library_writes_cleaned_script_to_single_txt_file(self):
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.json"
            library = ScriptLibrary(path)
            record = library.add_script(
                source_url="https://v.douyin.com/abc123",
                raw_script="原始文案",
                cleaned_script="优化后的文案。",
                video_path="output/douyin_library/a.mp4",
            )

            self.assertTrue(record["id"])
            self.assertEqual(record["status"], "ready")
            script_path = Path(record["script_path"])
            self.assertTrue(script_path.exists())
            self.assertEqual(script_path.read_text(encoding="utf-8"), "优化后的文案。")

            reloaded = ScriptLibrary(path)
            records = reloaded.list_scripts()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["cleaned_script"], "优化后的文案。")
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("raw_script", payload["scripts"][0])
            self.assertNotIn("cleaned_script", payload["scripts"][0])

            reloaded.mark_used(record["id"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["scripts"][0]["status"], "used")


class RuleCleanerTests(unittest.TestCase):
    def test_rule_cleaner_fixes_common_asr_errors_and_filters_fillers(self):
        from automation_suite.benchmark_ingestion.rule_cleaner import clean_transcript_rules

        result = clean_transcript_rules("嗯\n看挂这个食候\n然后呢借色很重要")

        self.assertIn("看卦这个时候。", result)
        self.assertIn("戒色很重要。", result)
        self.assertNotIn("嗯", result)


class AdaptationReviewerTests(unittest.TestCase):
    def test_parse_review_result_accepts_wrapped_json(self):
        from automation_suite.benchmark_ingestion.adaptation_reviewer import parse_review_result

        payload = """```json
        {
          "decision": "rewrite",
          "reason": "轻微作者自述，可去除后使用",
          "risk_tags": ["作者自述"],
          "adapted_script": "很多缘主最近会问，五月适合做哪些调整。"
        }
        ```"""

        result = parse_review_result(payload)

        self.assertEqual(result.decision, "rewrite")
        self.assertEqual(result.reason, "轻微作者自述，可去除后使用")
        self.assertEqual(result.risk_tags, ["作者自述"])
        self.assertEqual(result.adapted_script, "很多缘主最近会问，五月适合做哪些调整。")

    def test_parse_review_result_fails_closed_on_bad_json(self):
        from automation_suite.benchmark_ingestion.adaptation_reviewer import parse_review_result

        result = parse_review_result("这条文案看起来可以")

        self.assertEqual(result.decision, "reject")
        self.assertIn("解析失败", result.reason)
        self.assertEqual(result.risk_tags, ["review_failed"])
        self.assertEqual(result.adapted_script, "")

    def test_reviewer_prompt_uses_male_taoist_profile_and_conservative_filtering(self):
        from automation_suite.benchmark_ingestion.adaptation_reviewer import REVIEW_SYSTEM_PROMPT

        self.assertIn("男道士", REVIEW_SYSTEM_PROMPT)
        self.assertIn("男命理师", REVIEW_SYSTEM_PROMPT)
        self.assertIn("保守过滤", REVIEW_SYSTEM_PROMPT)
        self.assertIn("女性视角", REVIEW_SYSTEM_PROMPT)
        self.assertIn("时效错位", REVIEW_SYSTEM_PROMPT)
        self.assertIn("过往经历", REVIEW_SYSTEM_PROMPT)
        self.assertIn("默认 reject", REVIEW_SYSTEM_PROMPT)

    def test_reviewer_retries_when_model_output_is_truncated(self):
        from unittest.mock import patch

        from automation_suite.benchmark_ingestion.adaptation_reviewer import ScriptAdaptationReviewer

        class FakeResponse:
            status_code = 200

            def __init__(self, content, finish_reason):
                self._content = content
                self._finish_reason = finish_reason

            def json(self):
                return {
                    "choices": [
                        {
                            "finish_reason": self._finish_reason,
                            "message": {"content": self._content},
                        }
                    ]
                }

        responses = [
            FakeResponse('{"decision":"keep","reason":"', "length"),
            FakeResponse(
                '{"decision":"keep","reason":"可用","risk_tags":[],"adapted_script":"通用文案"}',
                "stop",
            ),
        ]

        with patch("automation_suite.benchmark_ingestion.adaptation_reviewer.requests.post", side_effect=responses) as post:
            reviewer = ScriptAdaptationReviewer(api_key="key", timeout=1)
            result = reviewer.review_text("很多缘主会问，为什么努力了运势还是迟迟打不开。")

        self.assertEqual(result.decision, "keep")
        self.assertEqual(result.reason, "可用")
        self.assertEqual(post.call_count, 2)
        first_payload = post.call_args_list[0].kwargs["json"]
        second_payload = post.call_args_list[1].kwargs["json"]
        self.assertGreater(second_payload["max_tokens"], first_payload["max_tokens"])


class LinkRouterTests(unittest.TestCase):
    def test_recognize_common_video_platform_url_types(self):
        from automation_suite.benchmark_ingestion.link_router import LinkType, recognize_url

        cases = [
            ("https://v.douyin.com/abc123", "douyin", LinkType.SHORTLINK),
            ("https://www.douyin.com/video/731234567890", "douyin", LinkType.SINGLE),
            ("https://www.douyin.com/user/MS4wLjABAAAA", "douyin", LinkType.ACCOUNT),
            ("https://space.bilibili.com/123456", "bilibili", LinkType.ACCOUNT),
            ("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili", LinkType.SINGLE),
            ("https://www.youtube.com/playlist?list=PLxxx", "youtube", LinkType.PLAYLIST),
            ("https://example.com/whatever", "unknown", LinkType.UNKNOWN),
        ]

        for url, platform, link_type in cases:
            with self.subTest(url=url):
                result = recognize_url(url)
                self.assertEqual(result.platform, platform)
                self.assertEqual(result.link_type, link_type)


if __name__ == "__main__":
    unittest.main()
