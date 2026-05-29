import tempfile
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


class FakeDownloader:
    def __init__(self):
        self.calls = 0

    def download(self, url, output_dir):
        self.calls += 1
        target = Path(output_dir) / "video.mp4"
        target.write_text("fake video", encoding="utf-8")
        return target


class FakeASR:
    def transcribe(self, video_path):
        return {
            "raw_text": "看挂这个食候",
            "segments": [{"start": 0, "end": 1, "text": "看挂这个食候"}],
        }


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def optimize_text(self, text):
        self.calls += 1
        return text.replace("看卦", "看卦").replace("。", "。")


class FakeAdaptationReviewer:
    def __init__(self, result):
        self.result = result

    def review_text(self, text):
        return self.result


class PipelineTests(unittest.TestCase):
    def test_pipeline_skips_processed_links_and_adds_new_script(self):
        from automation_suite.benchmark_ingestion.pipeline import BenchmarkIngestionPipeline
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = IngestionStateStore(root / "state.json")
            library = ScriptLibrary(root / "library.json")
            pipeline = BenchmarkIngestionPipeline(
                downloader=FakeDownloader(),
                asr_engine=FakeASR(),
                llm_client=FakeLLM(),
                state_store=state,
                script_library=library,
                video_library_dir=root / "videos",
            )

            first = pipeline.process_url("https://v.douyin.com/abc123")
            second = pipeline.process_url("https://v.douyin.com/abc123")

            self.assertEqual(first.status, "completed")
            self.assertEqual(second.status, "skipped")
            self.assertEqual(len(library.list_scripts()), 1)
            self.assertTrue(state.is_processed("https://v.douyin.com/abc123"))

    def test_pipeline_rejects_unsuitable_script_before_library(self):
        from automation_suite.benchmark_ingestion.adaptation_reviewer import AdaptationReviewResult
        from automation_suite.benchmark_ingestion.pipeline import BenchmarkIngestionPipeline
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = IngestionStateStore(root / "state.json")
            library = ScriptLibrary(root / "library.json")
            reviewer = FakeAdaptationReviewer(
                AdaptationReviewResult(
                    decision="reject",
                    reason="女性博主自述且绑定清明节时效",
                    risk_tags=["女性视角", "时效错位"],
                    adapted_script="",
                )
            )
            llm = FakeLLM()
            pipeline = BenchmarkIngestionPipeline(
                downloader=FakeDownloader(),
                asr_engine=FakeASR(),
                llm_client=llm,
                state_store=state,
                script_library=library,
                video_library_dir=root / "videos",
                adaptation_reviewer=reviewer,
            )

            result = pipeline.process_url("https://v.douyin.com/reject")

            self.assertEqual(result.status, "rejected")
            self.assertEqual(len(library.list_scripts()), 0)
            self.assertTrue(state.is_processed("https://v.douyin.com/reject"))
            record = state.get_url("https://v.douyin.com/reject")
            self.assertEqual(record["status"], "adaptation_rejected")
            self.assertEqual(record["adaptation_reason"], "女性博主自述且绑定清明节时效")
            self.assertEqual(record["adaptation_risk_tags"], ["女性视角", "时效错位"])
            self.assertEqual(llm.calls, 0)

    def test_pipeline_stores_rewritten_script_with_adaptation_meta(self):
        from automation_suite.benchmark_ingestion.adaptation_reviewer import AdaptationReviewResult
        from automation_suite.benchmark_ingestion.pipeline import BenchmarkIngestionPipeline
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = ScriptLibrary(root / "library.json")
            reviewer = FakeAdaptationReviewer(
                AdaptationReviewResult(
                    decision="rewrite",
                    reason="去掉原作者自述后可迁移",
                    risk_tags=["作者自述"],
                    adapted_script="很多缘主最近会问，五月适合做哪些调整。",
                )
            )
            pipeline = BenchmarkIngestionPipeline(
                downloader=FakeDownloader(),
                asr_engine=FakeASR(),
                llm_client=FakeLLM(),
                state_store=IngestionStateStore(root / "state.json"),
                script_library=library,
                video_library_dir=root / "videos",
                adaptation_reviewer=reviewer,
            )

            result = pipeline.process_url("https://v.douyin.com/rewrite")

            self.assertEqual(result.status, "completed")
            records = library.list_scripts()
            self.assertEqual(records[0]["cleaned_script"], "很多缘主最近会问，五月适合做哪些调整。")
            self.assertEqual(records[0]["meta"]["adaptation_decision"], "rewrite")
            self.assertEqual(records[0]["meta"]["adaptation_reason"], "去掉原作者自述后可迁移")
            self.assertEqual(records[0]["meta"]["adaptation_risk_tags"], ["作者自述"])

    def test_pipeline_keeps_script_library_meta_lean(self):
        from automation_suite.benchmark_ingestion.pipeline import BenchmarkIngestionPipeline
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = ScriptLibrary(root / "library.json")
            pipeline = BenchmarkIngestionPipeline(
                downloader=FakeDownloader(),
                asr_engine=FakeASR(),
                llm_client=FakeLLM(),
                state_store=IngestionStateStore(root / "state.json"),
                script_library=library,
                video_library_dir=root / "videos",
            )

            result = pipeline.process_url("https://v.douyin.com/lean")

            self.assertEqual(result.status, "completed")
            records = library.list_scripts()
            self.assertNotIn("asr_segments", records[0]["meta"])

    def test_pipeline_resumes_from_existing_downloaded_video(self):
        from automation_suite.benchmark_ingestion.pipeline import BenchmarkIngestionPipeline
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "videos" / "existing.mp4"
            video.parent.mkdir(parents=True)
            video.write_text("fake video", encoding="utf-8")
            state = IngestionStateStore(root / "state.json")
            state.update_url("https://v.douyin.com/resume", status="downloaded", video_path=str(video))
            downloader = FakeDownloader()
            pipeline = BenchmarkIngestionPipeline(
                downloader=downloader,
                asr_engine=FakeASR(),
                llm_client=FakeLLM(),
                state_store=state,
                script_library=ScriptLibrary(root / "library.json"),
                video_library_dir=root / "videos",
            )

            result = pipeline.process_url("https://v.douyin.com/resume")

            self.assertEqual(result.status, "completed")
            self.assertEqual(downloader.calls, 0)

    def test_downloader_builds_cookie_options(self):
        from automation_suite.benchmark_ingestion.downloader import YtDlpVideoDownloader

        downloader = YtDlpVideoDownloader(
            cookie_file=r"J:\cookies\douyin.txt",
            cookies_from_browser="edge",
        )
        opts = downloader._build_opts(Path("J:/out") / "%(title)s.%(ext)s")

        self.assertEqual(opts["cookiefile"], r"J:\cookies\douyin.txt")
        self.assertEqual(opts["cookiesfrombrowser"], ("edge",))

    def test_downloader_explains_dpapi_cookie_failure(self):
        from automation_suite.benchmark_ingestion.downloader import explain_yt_dlp_error

        message = explain_yt_dlp_error("Failed to decrypt with DPAPI")

        self.assertIn("无法解密浏览器 Cookie", message)
        self.assertIn("cookies.txt", message)

    def test_crtubeget_cookie_export_is_normalized_to_netscape_format(self):
        from automation_suite.benchmark_ingestion.douyin_cr import normalize_crck_cookie_output

        raw = (
            "Cookie: # Netscape HTTP Cookie File\n"
            "Cookie: .douyin.com\tTRUE\t/\tFALSE\t1893456000\tsid_tt\tsecret\n"
        )

        normalized = normalize_crck_cookie_output(raw)

        self.assertTrue(normalized.startswith("# Netscape HTTP Cookie File\n"))
        self.assertIn(".douyin.com\tTRUE\t/\tFALSE\t1893456000\tsid_tt\tsecret", normalized)
        self.assertNotIn("Cookie:", normalized)

    def test_crtubeget_aweme_detail_extracts_direct_video_url(self):
        from automation_suite.benchmark_ingestion.douyin_cr import parse_aweme_detail

        detail = {
            "aweme_detail": {
                "aweme_id": "7561459004695530811",
                "desc": "测试标题",
                "duration": 12345,
                "video": {
                    "play_addr": {
                        "url_list": [
                            "https://v5.example.com/playwm/video.mp4",
                            "https://backup.example.com/video.mp4",
                        ],
                    },
                    "cover": {"url_list": ["https://cover.example.com/a.webp"]},
                },
            },
        }

        resolved = parse_aweme_detail(detail, "https://www.douyin.com/video/7561459004695530811")

        self.assertEqual(resolved["id"], "7561459004695530811")
        self.assertEqual(resolved["title"], "测试标题")
        self.assertEqual(resolved["direct_url"], "https://v5.example.com/play/video.mp4")
        self.assertIn("https://v5.example.com/play/video.mp4", resolved["download_urls"])
        self.assertEqual(resolved["thumbnail"], "https://cover.example.com/a.webp")

    def test_crtubeget_aweme_detail_adds_aweme_play_and_bitrate_candidates(self):
        from automation_suite.benchmark_ingestion.douyin_cr import parse_aweme_detail

        detail = {
            "aweme_detail": {
                "aweme_id": "7561459004695530811",
                "desc": "测试标题",
                "video": {
                    "height": 1920,
                    "play_addr": {
                        "uri": "v0300fg10000test",
                        "url_list": ["https://v5.example.com/playwm/video.mp4"],
                    },
                    "bit_rate": [
                        {"play_addr": {"url_list": ["https://bitrate.example.com/video.mp4"]}},
                    ],
                },
            },
        }

        resolved = parse_aweme_detail(detail, "https://www.douyin.com/video/7561459004695530811")

        self.assertIn(
            "https://aweme.snssdk.com/aweme/v1/play/?video_id=v0300fg10000test&ratio=1080p&line=0",
            resolved["download_urls"],
        )
        self.assertIn("https://bitrate.example.com/video.mp4", resolved["download_urls"])

    def test_crtubeget_ab_js_uses_cache_when_remote_script_is_unavailable(self):
        import requests
        from unittest.mock import patch

        from automation_suite.benchmark_ingestion.douyin_cr import DouyinCRResolver

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qjs = root / "qjs.exe"
            qjs.write_text("fake qjs", encoding="utf-8")
            (root / "ab.js").write_text("window.ab=function(){return 'cached-ab';};", encoding="utf-8")
            resolver = DouyinCRResolver(root)

            with patch(
                "automation_suite.benchmark_ingestion.douyin_cr.requests.get",
                side_effect=requests.exceptions.HTTPError("503 Server Error"),
            ), patch("automation_suite.benchmark_ingestion.douyin_cr.subprocess.check_output", return_value="cached-ab\n"):
                result = resolver._a_bogus("aweme_id=1", root)

        self.assertEqual(result, "cached-ab")

    def test_downloader_uses_douyin_fallback_when_fresh_cookie_failure(self):
        from automation_suite.benchmark_ingestion.downloader import DownloadError, YtDlpVideoDownloader

        class FallbackDownloader:
            def __init__(self):
                self.called = False

            def download(self, url, output_dir):
                self.called = True
                target = Path(output_dir) / "fallback.mp4"
                target.write_text("video", encoding="utf-8")
                return target

        class BrokenDownloader(YtDlpVideoDownloader):
            def _download_with_yt_dlp(self, url, output_root, outtmpl):
                raise DownloadError("Fresh cookies are needed")

        with tempfile.TemporaryDirectory() as tmp:
            fallback = FallbackDownloader()
            downloader = BrokenDownloader(douyin_fallback_downloader=fallback)

            path = downloader.download("https://v.douyin.com/abc123/", tmp)

            self.assertTrue(fallback.called)
            self.assertEqual(path.name, "fallback.mp4")

    def test_downloader_uses_douyin_fallback_first_for_douyin_links(self):
        from automation_suite.benchmark_ingestion.downloader import YtDlpVideoDownloader

        class FallbackDownloader:
            def __init__(self):
                self.called = False

            def download(self, url, output_dir):
                self.called = True
                target = Path(output_dir) / "fallback-first.mp4"
                target.write_text("video", encoding="utf-8")
                return target

        class TrackingDownloader(YtDlpVideoDownloader):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.ytdlp_called = False

            def _download_with_yt_dlp(self, url, output_root, outtmpl):
                self.ytdlp_called = True
                target = Path(output_root) / "yt-dlp.mp4"
                target.write_text("video", encoding="utf-8")
                return target

        with tempfile.TemporaryDirectory() as tmp:
            fallback = FallbackDownloader()
            downloader = TrackingDownloader(douyin_fallback_downloader=fallback)

            path = downloader.download("https://www.douyin.com/video/7636005355827525033", tmp)

            self.assertTrue(fallback.called)
            self.assertFalse(downloader.ytdlp_called)
            self.assertEqual(path.name, "fallback-first.mp4")

    def test_crtubeget_downloader_retries_after_stream_error(self):
        import requests
        from automation_suite.benchmark_ingestion.douyin_cr import DouyinCRVideoDownloader

        class FakeResolver:
            def resolve(self, url):
                return {
                    "id": "1",
                    "title": "video",
                    "referer": url,
                    "direct_url": "https://example.com/a.mp4",
                    "download_urls": ["https://example.com/a.mp4", "https://example.com/b.mp4"],
                }

        class FlakyDownloader(DouyinCRVideoDownloader):
            def __init__(self):
                self.resolver = FakeResolver()
                self.timeout = 1
                self.calls = []

            def _download_candidate(self, candidate, tmp_target, headers):
                self.calls.append(candidate)
                if len(self.calls) == 1:
                    tmp_target.write_bytes(b"partial")
                    raise requests.exceptions.ChunkedEncodingError("broken stream")
                tmp_target.write_bytes(b"complete")

        with tempfile.TemporaryDirectory() as tmp:
            downloader = FlakyDownloader()
            path = downloader.download("https://www.douyin.com/video/1", tmp)

            self.assertEqual(path.read_bytes(), b"complete")
            self.assertGreaterEqual(len(downloader.calls), 2)

    def test_external_asr_engine_reads_batch_asr_outputs(self):
        from automation_suite.benchmark_ingestion.external_asr_engine import ExternalBatchASREngine

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "scripts" / "batch_asr.py"
            script.parent.mkdir(parents=True)
            script.write_text(
                "from pathlib import Path\n"
                "import argparse, json\n"
                "p=argparse.ArgumentParser()\n"
                "p.add_argument('--input'); p.add_argument('--txt'); p.add_argument('--json')\n"
                "p.add_argument('--srt'); p.add_argument('--logs')\n"
                "p.add_argument('--model'); p.add_argument('--device'); p.add_argument('--compute-type')\n"
                "p.add_argument('--language'); p.add_argument('--limit'); p.add_argument('--force', action='store_true')\n"
                "args=p.parse_args()\n"
                "video=next(Path(args.input).glob('*.mp4'))\n"
                "Path(args.txt).mkdir(parents=True, exist_ok=True)\n"
                "Path(args.json).mkdir(parents=True, exist_ok=True)\n"
                "Path(args.srt).mkdir(parents=True, exist_ok=True)\n"
                "Path(args.logs).mkdir(parents=True, exist_ok=True)\n"
                "Path(args.txt, video.stem + '.txt').write_text('本地 ASR 文案', encoding='utf-8')\n"
                "Path(args.json, video.stem + '.json').write_text(json.dumps({"
                "'language':'zh','duration':1.2,'segments':[{'id':0,'start':0,'end':1.2,'text':'本地 ASR 文案'}]"
                "}, ensure_ascii=False), encoding='utf-8')\n",
                encoding="utf-8",
            )
            video = root / "source.mp4"
            video.write_bytes(b"fake")
            engine = ExternalBatchASREngine(asr_root=root, python_executable=sys.executable)

            result = engine.transcribe(video)

            self.assertEqual(result["raw_text"], "本地 ASR 文案")
            self.assertEqual(result["language"], "zh")
            self.assertEqual(result["segments"][0]["text"], "本地 ASR 文案")

    def test_asr_cleaner_strips_llm_wrappers(self):
        from automation_suite.benchmark_ingestion.llm_cleaner import strip_llm_wrappers

        wrapped = "```text\n清洗后文案：这是清洗后的口播。\n```"

        self.assertEqual(strip_llm_wrappers(wrapped), "这是清洗后的口播。")

    def test_asr_cleaner_prompt_is_for_calibration_not_rewriting(self):
        from automation_suite.benchmark_ingestion.llm_cleaner import SYSTEM_PROMPT

        self.assertIn("ASR", SYSTEM_PROMPT)
        self.assertIn("不要改写", SYSTEM_PROMPT)
        self.assertIn("不要扩写", SYSTEM_PROMPT)

    def test_asr_cleaner_retries_after_timeout(self):
        import requests
        from automation_suite.benchmark_ingestion.llm_cleaner import ASRCleaningLLMClient

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "清洗后的文案"}}]}

        calls = {"count": 0}

        def fake_post(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise requests.exceptions.ReadTimeout("timeout")
            return FakeResponse()

        client = ASRCleaningLLMClient(api_key="key", timeout=1, max_retries=1, retry_delay=0)
        with patch("automation_suite.benchmark_ingestion.llm_cleaner.requests.post", side_effect=fake_post):
            result = client.optimize_text("原始文案")

        self.assertEqual(result, "清洗后的文案")
        self.assertEqual(calls["count"], 2)

    def test_douyin_profile_extracts_sec_uid_from_profile_url(self):
        from automation_suite.benchmark_ingestion.douyin_profile import extract_sec_uid

        url = (
            "https://www.iesdouyin.com/share/user/MS4wLjABAAAACnR?"
            "with_sec_did=1&sec_uid=MS4wLjABAAAACnR&from_ssr=1"
        )

        self.assertEqual(extract_sec_uid(url), "MS4wLjABAAAACnR")

    def test_douyin_profile_parses_post_list_to_video_links(self):
        from automation_suite.benchmark_ingestion.douyin_profile import parse_post_list

        payload = {
            "aweme_list": [
                {"aweme_id": "7501", "desc": "第一条"},
                {"aweme_id": "7502", "desc": "第二条"},
                {"aweme_id": "", "desc": "无效"},
            ],
            "has_more": 0,
            "max_cursor": 0,
        }

        result = parse_post_list(payload)

        self.assertEqual(
            result["links"],
            ["https://www.douyin.com/video/7501", "https://www.douyin.com/video/7502"],
        )
        self.assertFalse(result["has_more"])


if __name__ == "__main__":
    unittest.main()
