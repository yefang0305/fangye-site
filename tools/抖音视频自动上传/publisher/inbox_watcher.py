"""Inbox watcher: cross-process video drop from VideoCut → MediaPush.

VideoCut writes a batch directory under `inbox/`:

    inbox/<YYYYMMDD-HHMMSS>-<slot>/
        manifest.json     # {scheduled_time, videos: [...], ...}
        v1.mp4
        v2.mp4
        ...

This watcher polls `inbox/` every `poll_sec` seconds. For each batch that
has a manifest.json and no `.processing` marker:

  1. Mark `.processing` to prevent double-handling
  2. Parse manifest, validate
  3. List active groups; if `len(active_groups) < len(videos)`, log error and
     leave the batch alone (don't move) so user can fix and the watcher will
     retry next tick
  4. Random-shuffle active groups, pair 1:1 with videos (in manifest order)
  5. For each pair, call `queue.submit(video_abs_path, scheduled_time, group_id)`
  6. Write `result.json` with task_id / group_id mapping
  7. Move whole batch_dir to `processed/<batch_id>/`

Designed to run in a `QThread`, but the main work happens in `process_once()`
which is called both by the loop and by tests (no Qt dependency).
"""
from __future__ import annotations

import json
import random
import shutil
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QThread

from db.store import Store


_PROCESSING_MARKER = ".processing"
_MANIFEST_NAME = "manifest.json"
_RESULT_NAME = "result.json"
_ERROR_LOG_NAME = "error.log"
# Re-claim a stuck `.processing` marker if older than this (process crashed mid-handling)
_STUCK_MARKER_AGE_SEC = 60 * 60  # 1 hour

# Backoff schedule for repeated identical errors on the same batch.
# After N consecutive failures with the same error message, the watcher
# waits this many seconds before trying that batch again. Keeps error.log
# from exploding when a batch is permanently broken.
_BACKOFF_SCHEDULE_SEC = [0, 0, 0, 60, 60, 300, 300, 600]   # index = consecutive_count - 1
_BACKOFF_MAX_SEC = 600


class InboxWatcher(QThread):
    def __init__(
        self,
        store: Store,
        queue,                       # PublishQueue (typed loosely to keep tests free of Qt)
        inbox_dir: str,
        processed_dir: str,
        poll_sec: float = 5.0,
    ):
        super().__init__()
        self._store = store
        self._queue = queue
        self._inbox = Path(inbox_dir)
        self._processed = Path(processed_dir)
        self._poll_sec = poll_sec
        self._stop = threading.Event()
        self._inbox.mkdir(parents=True, exist_ok=True)
        self._processed.mkdir(parents=True, exist_ok=True)
        # Per-batch error state for dedup + backoff:
        #   batch_dir.name → {"signature": str, "count": int, "next_attempt_ts": float}
        # In-memory only; rebuilt from scratch on watcher restart (which is fine —
        # restart is itself a chance to retry sooner).
        self._error_state: dict[str, dict] = {}

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:  # QThread entry
        while not self._stop.is_set():
            try:
                self.process_once()
            except Exception:
                traceback.print_exc()
            # Sleep in small chunks so stop() is responsive
            slept = 0.0
            while slept < self._poll_sec and not self._stop.is_set():
                time.sleep(0.2)
                slept += 0.2

    # ---- core ----
    def process_once(self) -> int:
        """Process all eligible batches once. Returns number processed."""
        count = 0
        # Drop state for batches that no longer exist (got moved to processed/
        # or deleted by user)
        live_names = {p.name for p in self._inbox.iterdir() if p.is_dir()}
        for stale in [k for k in self._error_state if k not in live_names]:
            self._error_state.pop(stale, None)

        now = time.time()
        for batch_dir in sorted(self._inbox.iterdir()):
            if not batch_dir.is_dir():
                continue
            if batch_dir.resolve() == self._processed.resolve():
                continue  # never recurse into processed/
            # Honor backoff for batches that keep failing with the same error
            state = self._error_state.get(batch_dir.name)
            if state and state.get("next_attempt_ts", 0) > now:
                continue
            manifest_path = batch_dir / _MANIFEST_NAME
            if not manifest_path.is_file():
                continue
            marker = batch_dir / _PROCESSING_MARKER
            if marker.exists():
                # Stuck? Reclaim if old.
                age = time.time() - marker.stat().st_mtime
                if age < _STUCK_MARKER_AGE_SEC:
                    continue
                marker.unlink(missing_ok=True)
            try:
                marker.touch()
                self._handle_batch(batch_dir, manifest_path)
                # Success → clear any backoff state
                self._error_state.pop(batch_dir.name, None)
                count += 1
            except Exception as e:  # noqa: BLE001
                signature = f"{type(e).__name__}: {e}"
                self._record_error(batch_dir, signature, traceback.format_exc())
                marker.unlink(missing_ok=True)
        return count

    def _record_error(self, batch_dir: Path, signature: str, full_traceback: str) -> None:
        """Update error state + log only when meaningful (new error or every Nth repeat)."""
        prev = self._error_state.get(batch_dir.name)
        if prev and prev["signature"] == signature:
            prev["count"] += 1
            count = prev["count"]
            backoff = _BACKOFF_SCHEDULE_SEC[min(count - 1, len(_BACKOFF_SCHEDULE_SEC) - 1)]
            backoff = max(backoff, self._poll_sec)
            prev["next_attempt_ts"] = time.time() + backoff
            # Log every repeat threshold transition: count==3, 6, 11, 21, ...
            if count in (3, 6, 11, 21, 51, 101):
                self._write_error_line(
                    batch_dir,
                    f"(同样错误已连续 {count} 次，下次 {int(backoff)} 秒后重试) {signature}",
                )
            # Otherwise stay quiet — caller already knows from the first log
            return
        # New error (or different from last) → log full traceback fresh
        self._error_state[batch_dir.name] = {
            "signature": signature,
            "count": 1,
            "next_attempt_ts": time.time() + self._poll_sec,
        }
        self._write_error_line(batch_dir, f"{signature}\n{full_traceback}")

    def _handle_batch(self, batch_dir: Path, manifest_path: Path) -> None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        batch_id = manifest.get("batch_id") or batch_dir.name
        sched_str = manifest["scheduled_time"]
        scheduled = datetime.fromisoformat(sched_str)
        videos = manifest["videos"]
        if not isinstance(videos, list) or not videos:
            raise ValueError("manifest.videos must be a non-empty list")

        active_groups = [g for g in self._store.list_groups()
                         if any(a["is_active"] == 1 for a in self._store.list_accounts(group_id=g["id"]))]
        if len(active_groups) < len(videos):
            raise ValueError(
                f"not enough active groups: need {len(videos)}, have {len(active_groups)}"
            )

        # Random shuffle, take first N to pair with videos in their manifest order
        groups_pool = active_groups[:]
        random.shuffle(groups_pool)
        pairings = list(zip(videos, groups_pool[:len(videos)]))

        results = []
        for filename, group in pairings:
            video_abs = (batch_dir / filename).resolve()
            if not video_abs.is_file():
                raise FileNotFoundError(f"manifest references missing file: {filename}")
            task_id = self._queue.submit(str(video_abs), scheduled, group["id"])
            results.append({
                "video": filename,
                "group_id": group["id"],
                "group_name": group["name"],
                "task_id": task_id,
            })

        # Write result.json before moving so we have an audit trail even if move fails
        (batch_dir / _RESULT_NAME).write_text(
            json.dumps({
                "batch_id": batch_id,
                "scheduled_time": sched_str,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "pairings": results,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Clean up the marker before moving the directory
        (batch_dir / _PROCESSING_MARKER).unlink(missing_ok=True)

        # NOTE: video files are referenced by absolute path in the queue's task
        # records, so moving the directory is safe ONLY if the queue stores the
        # original path. Since process_one looks up the file at upload time,
        # we keep the videos in the same place but move them to processed/.
        # Update the absolute path in DB before moving.
        target = self._processed / batch_dir.name
        if target.exists():
            target = self._processed / f"{batch_dir.name}-{int(time.time())}"
        # Move directory atomically (same volume — both under inbox/)
        shutil.move(str(batch_dir), str(target))
        # Patch each task's video_path to the new location
        for entry in results:
            new_path = (target / entry["video"]).resolve()
            self._store._conn.execute(
                "UPDATE tasks SET video_path = ? WHERE id = ?",
                (str(new_path), entry["task_id"]),
            )
        self._store._conn.commit()

    def _write_error_line(self, batch_dir: Path, msg: str) -> None:
        try:
            log = batch_dir / _ERROR_LOG_NAME
            stamp = datetime.now().isoformat(timespec="seconds")
            with log.open("a", encoding="utf-8") as f:
                f.write(f"[{stamp}] {msg}\n")
        except Exception:
            pass  # never let logging kill the watcher
