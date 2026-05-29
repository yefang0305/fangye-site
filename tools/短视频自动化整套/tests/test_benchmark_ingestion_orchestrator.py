import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FakeExpansion:
    links: list[str]


class FakeExpander:
    def __init__(self, links):
        self.links = links
        self.calls = []

    def expand(self, profile_url):
        self.calls.append(profile_url)
        return FakeExpansion(list(self.links))


class FakeDownloader:
    def __init__(self, fail_urls=None):
        self.fail_urls = set(fail_urls or [])
        self.calls = []

    def download(self, url, output_dir):
        self.calls.append(url)
        if url in self.fail_urls:
            raise RuntimeError("download boom")
        target = Path(output_dir) / f"{url.rsplit('/', 1)[-1]}.mp4"
        target.write_text("fake video", encoding="utf-8")
        return target


class FakeASR:
    def __init__(self, texts=None):
        self.texts = texts or {}

    def transcribe(self, video_path):
        key = Path(video_path).stem
        return {
            "raw_text": self.texts.get(key, "嗯\n看挂这个食候"),
            "segments": [{"start": 0, "end": 1, "text": key}],
            "language": "zh",
            "duration": 1.0,
        }


class FakeLLM:
    def __init__(self):
        self.inputs = []

    def optimize_text(self, text):
        self.inputs.append(text)
        return f"LLM:{text}"


class FakeReviewer:
    model = "fake-reviewer"

    def __init__(self, decisions):
        self.decisions = list(decisions)

    def review_text(self, text):
        from automation_suite.benchmark_ingestion.adaptation_reviewer import AdaptationReviewResult

        decision = self.decisions.pop(0)
        if decision == "reject":
            return AdaptationReviewResult(decision="reject", reason="不适配", risk_tags=["risk"])
        if decision == "rewrite":
            return AdaptationReviewResult(
                decision="rewrite",
                reason="可改写",
                risk_tags=["minor"],
                adapted_script="改写后的可用文案。",
            )
        return AdaptationReviewResult(decision="keep", reason="可用")


class BenchmarkAgentOrchestratorTests(unittest.TestCase):
    def test_run_profile_expands_links_applies_limit_creates_video_dir_and_summarizes(self):
        from automation_suite.benchmark_ingestion.orchestrator import BenchmarkAgentOrchestrator
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_dir = root / "videos"
            library = ScriptLibrary(root / "library.json")
            state = IngestionStateStore(root / "state.json")
            expander = FakeExpander(
                [
                    "https://www.douyin.com/video/1",
                    "https://www.douyin.com/video/2",
                    "https://www.douyin.com/video/3",
                ]
            )
            downloader = FakeDownloader()

            result = BenchmarkAgentOrchestrator(
                profile_expander=expander,
                downloader=downloader,
                asr_engine=FakeASR(),
                llm_client=FakeLLM(),
                adaptation_reviewer=None,
                script_library=library,
                video_library_dir=video_dir,
                state_store=state,
            ).run_profile("https://www.douyin.com/user/sec_uid", limit=2)

            self.assertTrue(video_dir.exists())
            self.assertEqual(expander.calls, ["https://www.douyin.com/user/sec_uid"])
            self.assertEqual(downloader.calls, ["https://www.douyin.com/video/1", "https://www.douyin.com/video/2"])
            self.assertEqual(result["expanded_count"], 3)
            self.assertEqual(result["selected_count"], 2)
            self.assertEqual(result["completed"], 2)
            self.assertEqual(result["rejected"], 0)
            self.assertEqual(result["failed"], 0)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual([item["status"] for item in result["items"]], ["completed", "completed"])
            self.assertEqual(len(library.list_scripts()), 2)
            self.assertIn("LLM:看卦这个时候。", library.list_scripts()[0]["cleaned_script"])

    def test_run_profile_rejects_and_rewrites_with_adaptation_reviewer(self):
        from automation_suite.benchmark_ingestion.orchestrator import BenchmarkAgentOrchestrator
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = ScriptLibrary(root / "library.json")
            state = IngestionStateStore(root / "state.json")

            result = BenchmarkAgentOrchestrator(
                profile_expander=FakeExpander(["https://www.douyin.com/video/reject", "https://www.douyin.com/video/rewrite"]),
                downloader=FakeDownloader(),
                asr_engine=FakeASR(),
                llm_client=None,
                adaptation_reviewer=FakeReviewer(["reject", "rewrite"]),
                script_library=library,
                video_library_dir=root / "videos",
                state_store=state,
            ).run_profile("https://www.douyin.com/user/sec_uid")

            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["rejected"], 1)
            self.assertEqual(result["failed"], 0)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual([item["status"] for item in result["items"]], ["rejected", "completed"])
            self.assertEqual(len(library.list_scripts()), 1)
            self.assertEqual(library.list_scripts()[0]["cleaned_script"], "改写后的可用文案。")
            self.assertEqual(state.get_url("https://www.douyin.com/video/reject")["status"], "adaptation_rejected")

    def test_run_profile_marks_item_failed_and_continues(self):
        from automation_suite.benchmark_ingestion.orchestrator import BenchmarkAgentOrchestrator
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_url = "https://www.douyin.com/video/bad"
            good_url = "https://www.douyin.com/video/good"
            state = IngestionStateStore(root / "state.json")

            with self.assertLogs("BenchmarkIngestion.Pipeline", level="ERROR") as logs:
                result = BenchmarkAgentOrchestrator(
                    profile_expander=FakeExpander([bad_url, good_url]),
                    downloader=FakeDownloader(fail_urls={bad_url}),
                    asr_engine=FakeASR(),
                    llm_client=None,
                    adaptation_reviewer=None,
                    script_library=ScriptLibrary(root / "library.json"),
                    video_library_dir=root / "videos",
                    state_store=state,
                ).run_profile("https://www.douyin.com/user/sec_uid")

            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["failed"], 1)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual([item["status"] for item in result["items"]], ["failed", "completed"])
            self.assertIn("download boom", result["items"][0]["message"])
            self.assertEqual(state.get_url(bad_url)["status"], "failed")
            self.assertIn("Benchmark ingestion failed", logs.output[0])

    def test_run_profile_counts_previously_processed_links_as_skipped(self):
        from automation_suite.benchmark_ingestion.orchestrator import BenchmarkAgentOrchestrator
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            done_url = "https://www.douyin.com/video/done"
            state = IngestionStateStore(root / "state.json")
            state.update_url(done_url, status="llm_done", script_id="existing")
            downloader = FakeDownloader()

            result = BenchmarkAgentOrchestrator(
                profile_expander=FakeExpander([done_url]),
                downloader=downloader,
                asr_engine=FakeASR(),
                llm_client=None,
                adaptation_reviewer=None,
                script_library=ScriptLibrary(root / "library.json"),
                video_library_dir=root / "videos",
                state_store=state,
            ).run_profile("https://www.douyin.com/user/sec_uid")

            self.assertEqual(result["completed"], 0)
            self.assertEqual(result["failed"], 0)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["items"][0]["status"], "skipped")
            self.assertEqual(downloader.calls, [])

    def test_run_profile_limit_counts_unprocessed_links_only(self):
        from automation_suite.benchmark_ingestion.orchestrator import BenchmarkAgentOrchestrator
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            done_url = "https://www.douyin.com/video/done"
            next_url = "https://www.douyin.com/video/next"
            state = IngestionStateStore(root / "state.json")
            state.update_url(done_url, status="llm_done", script_id="existing")
            downloader = FakeDownloader()

            result = BenchmarkAgentOrchestrator(
                profile_expander=FakeExpander([done_url, next_url]),
                downloader=downloader,
                asr_engine=FakeASR(),
                llm_client=None,
                adaptation_reviewer=None,
                script_library=ScriptLibrary(root / "library.json"),
                video_library_dir=root / "videos",
                state_store=state,
            ).run_profile("https://www.douyin.com/user/sec_uid", limit=1)

            self.assertEqual(result["selected_count"], 1)
            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual(downloader.calls, [next_url])
            self.assertEqual(result["items"][0]["url"], next_url)

    def test_run_profile_skips_links_after_reaching_failure_limit(self):
        from automation_suite.benchmark_ingestion.orchestrator import BenchmarkAgentOrchestrator
        from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
        from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_url = "https://www.douyin.com/video/bad"
            next_url = "https://www.douyin.com/video/next"
            state = IngestionStateStore(root / "state.json")
            downloader = FakeDownloader(fail_urls={bad_url})
            orchestrator = BenchmarkAgentOrchestrator(
                profile_expander=FakeExpander([bad_url, next_url]),
                downloader=downloader,
                asr_engine=FakeASR(),
                llm_client=None,
                adaptation_reviewer=None,
                script_library=ScriptLibrary(root / "library.json"),
                video_library_dir=root / "videos",
                state_store=state,
            )

            for _ in range(3):
                result = orchestrator.run_profile("https://www.douyin.com/user/sec_uid", limit=1)
                self.assertEqual(result["items"][0]["url"], bad_url)
                self.assertEqual(result["items"][0]["status"], "failed")

            locked = state.get_url(bad_url)
            self.assertEqual(locked["status"], "permanent_failed")
            self.assertEqual(locked["failure_count"], 3)

            result = orchestrator.run_profile("https://www.douyin.com/user/sec_uid", limit=1)

            self.assertEqual(result["selected_count"], 1)
            self.assertEqual(result["items"][0]["url"], next_url)
            self.assertEqual(result["completed"], 1)


if __name__ == "__main__":
    unittest.main()
