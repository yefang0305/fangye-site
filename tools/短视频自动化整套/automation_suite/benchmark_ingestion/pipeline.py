from __future__ import annotations

from pathlib import Path
import logging

from .models import ProcessResult, stable_url_hash
from .rule_cleaner import clean_transcript_rules

logger = logging.getLogger("BenchmarkIngestion.Pipeline")


class BenchmarkIngestionPipeline:
    """End-to-end benchmark video ingestion pipeline.

    Flow:
        1. Check state store → skip if already processed
        2. Download video (yt-dlp + CR TubeGet fallback)
        3. Transcribe via ASR (local faster-whisper or external)
        4. Rule-based text cleaning
        5. Adaptation review (LLM-based persona/risk filter)
        6. LLM cleanup (optional, after rule cleaning)
        7. Store script in library

    Each step is tracked in the state store for resume capability.
    """

    def __init__(
        self,
        downloader,
        asr_engine,
        llm_client,
        state_store,
        script_library,
        video_library_dir: str | Path,
        adaptation_reviewer=None,
        max_failures: int = 3,
    ):
        self.downloader = downloader
        self.asr_engine = asr_engine
        self.llm_client = llm_client
        self.adaptation_reviewer = adaptation_reviewer
        self.state_store = state_store
        self.script_library = script_library
        self.video_library_dir = Path(video_library_dir)
        self.video_library_dir.mkdir(parents=True, exist_ok=True)
        self.max_failures = max(1, int(max_failures or 1))

    def process_url(self, url: str) -> ProcessResult:
        if self.state_store.is_processed(url):
            return ProcessResult(url=url, status="skipped", message="已处理，跳过")

        try:
            record = self.state_store.get_url(url)
            existing_video = Path(record.get("video_path", "")) if record.get("video_path") else None
            if existing_video and existing_video.exists() and record.get("status") in {"downloaded", "asr_done", "failed"}:
                video_path = existing_video
            else:
                self.state_store.update_url(url, status="downloading", error="")
                video_path = Path(self.downloader.download(url, self.video_library_dir))
                self.state_store.update_url(url, status="downloaded", video_path=str(video_path), error="")

            asr_result = self.asr_engine.transcribe(video_path)
            raw_script = (asr_result.get("raw_text") or "").strip()
            if not raw_script:
                raise RuntimeError("ASR 未返回文案")
            self.state_store.update_url(url, status="asr_done")

            rule_cleaned = clean_transcript_rules(raw_script) or raw_script
            review = self._review_adaptation(rule_cleaned)
            if review and review.decision == "reject":
                self.state_store.update_url(
                    url,
                    status="adaptation_rejected",
                    video_path=str(video_path),
                    adaptation_reason=review.reason,
                    adaptation_risk_tags=review.risk_tags,
                    error="",
                )
                return ProcessResult(url=url, status="rejected", message=review.reason, video_path=str(video_path))

            adaptation_meta = {}
            if review:
                adaptation_meta = {
                    "adaptation_decision": review.decision,
                    "adaptation_reason": review.reason,
                    "adaptation_risk_tags": review.risk_tags,
                    "adaptation_model": getattr(self.adaptation_reviewer, "model", ""),
                }
            if review and review.decision == "rewrite" and review.adapted_script.strip():
                final_script = review.adapted_script.strip()
            else:
                final_script = self._llm_cleanup(rule_cleaned)

            record = self.script_library.add_script(
                source_url=url,
                raw_script=raw_script,
                cleaned_script=final_script,
                video_path=str(video_path),
                meta={
                    "url_hash": stable_url_hash(url),
                    "asr_language": asr_result.get("language", ""),
                    "asr_duration": asr_result.get("duration"),
                    **adaptation_meta,
                },
            )
            self.state_store.update_url(url, status="llm_done", script_id=record["id"], error="")
            return ProcessResult(url=url, status="completed", video_path=str(video_path), script_id=record["id"])
        except Exception as exc:
            logger.exception("Benchmark ingestion failed: %s", url)
            failure_count = int(self.state_store.get_url(url).get("failure_count", 0) or 0) + 1
            status = "permanent_failed" if failure_count >= self.max_failures else "failed"
            self.state_store.update_url(
                url,
                status=status,
                error=str(exc),
                failure_count=failure_count,
            )
            return ProcessResult(url=url, status="failed", message=str(exc))

    def process_urls(self, urls: list[str], progress=None) -> list[ProcessResult]:
        results = []
        for index, url in enumerate(urls, start=1):
            if progress:
                progress(index, len(urls), url)
            results.append(self.process_url(url))
        return results

    def _llm_cleanup(self, text: str) -> str:
        if not self.llm_client:
            return text
        optimized = self.llm_client.optimize_text(text)
        return (optimized or text).strip()

    def _review_adaptation(self, text: str):
        if not self.adaptation_reviewer:
            return None
        return self.adaptation_reviewer.review_text(text)
