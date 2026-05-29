from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import now_iso, stable_url_hash
from .pipeline import BenchmarkIngestionPipeline


class _InMemoryStateStore:
    """In-memory state store for testing or stateless orchestration."""

    def __init__(self):
        self._records: dict[str, dict[str, Any]] = {}

    def is_processed(self, url: str) -> bool:
        return self.get_url(url).get("status") in {"llm_done", "completed", "adaptation_rejected", "permanent_failed"}

    def get_url(self, url: str) -> dict[str, Any]:
        return self._records.get(stable_url_hash(url), {})

    def update_url(self, url: str, **fields) -> dict[str, Any]:
        key = stable_url_hash(url)
        record = self._records.get(key, {"url": url, "created_at": now_iso()})
        record.update(fields)
        record["updated_at"] = now_iso()
        self._records[key] = record
        return record


class BenchmarkAgentOrchestrator:
    """Top-level orchestrator for benchmark profile ingestion.

    Coordinates:
    1. Profile expansion (extract all video links from an account)
    2. Link selection (respect limit, skip already processed)
    3. Pipeline processing (download → ASR → clean → review → store)
    4. Summary reporting
    """

    def __init__(
        self,
        profile_expander,
        downloader,
        asr_engine,
        llm_client,
        adaptation_reviewer,
        script_library,
        video_library_dir: str | Path,
        state_store=None,
        max_failures: int = 3,
    ):
        self.profile_expander = profile_expander
        self.video_library_dir = Path(video_library_dir)
        self.video_library_dir.mkdir(parents=True, exist_ok=True)
        self.state_store = state_store or _InMemoryStateStore()
        self.pipeline = BenchmarkIngestionPipeline(
            downloader=downloader,
            asr_engine=asr_engine,
            llm_client=llm_client,
            state_store=self.state_store,
            script_library=script_library,
            video_library_dir=self.video_library_dir,
            adaptation_reviewer=adaptation_reviewer,
            max_failures=max_failures,
        )

    def run_profile(self, profile_url: str, limit: int = 0) -> dict:
        expansion = self.profile_expander.expand(profile_url)
        links = list(getattr(expansion, "links", []) or [])
        selected = self._select_links(links, limit)

        items = []
        counts = {"completed": 0, "rejected": 0, "failed": 0, "skipped": 0}
        for url in selected:
            result = self.pipeline.process_url(url)
            status = result.status if result.status in counts else "failed"
            counts[status] += 1
            items.append(
                {
                    "url": result.url,
                    "status": status,
                    "script_id": result.script_id,
                    "message": result.message,
                }
            )

        return {
            "profile_url": profile_url,
            "expanded_count": len(links),
            "selected_count": len(selected),
            "completed": counts["completed"],
            "rejected": counts["rejected"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "items": items,
        }

    def _select_links(self, links: list[str], limit: int) -> list[str]:
        if not limit or limit <= 0:
            return links

        selected = []
        for url in links:
            if self.state_store.is_processed(url):
                continue
            selected.append(url)
            if len(selected) >= limit:
                break
        return selected
