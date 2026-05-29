"""Publish task queue.

Runs in a dedicated QThread; emits Qt signals on status changes so the UI
can refresh without polling. Tasks are processed strictly sequentially —
one Chromium instance at a time — to keep memory bounded.
"""
from __future__ import annotations

import queue as _queue
import re
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from db.store import Store
from publisher.base import Publisher


_MIN_VIDEO_BYTES = 1_000_000   # 1 MB
_ALLOWED_EXT = {".mp4"}
SCHEDULED_MIN_HOURS = 2         # platforms (Douyin etc.) require >=2h lead time

# Per-attempt upload timeout. Headless attempts can run as long as the platform
# needs (large videos, slow networks). Headed attempts have a tight 3-minute
# budget — if the user isn't at the keyboard to solve the captcha, we want to
# stop blocking the queue and move on.
_TIMEOUT_HEADLESS_SEC = 15 * 60
_TIMEOUT_HEADED_SEC = 3 * 60

# Headless = first attempt only. Any subsequent attempt (auto-retry once OR
# manual retry from the UI) flips to headed mode so the user can intervene.
def _headless_for_attempt(attempt_count: int) -> bool:
    return attempt_count == 1

# Auto-retry policy: when attempt 1 fails, immediately re-enqueue once in
# headed mode. After that headed attempt fails, the log stays "failed" until
# the user manually retries (which also runs headed).
AUTO_HEADED_RETRY = True

# Strip trailing _<digits> from filename stem before using as title.
# VideoCut produces files like "养生秘诀_3.mp4" for the 3rd variant of a script;
# the trailing version marker shouldn't appear on Douyin.
_TITLE_SUFFIX_RE = re.compile(r"_\d+$")


def _clean_title(stem: str) -> str:
    return _TITLE_SUFFIX_RE.sub("", stem)


class PublishQueue(QThread):
    # (task_log_id, account_id, status_str)
    status_changed = pyqtSignal(int, int, str)

    def __init__(self, store: Store, publishers: dict[str, Publisher]):
        super().__init__()
        self._store = store
        self._publishers = publishers
        self._inbox: _queue.Queue[int] = _queue.Queue()  # holds task_log_ids
        self._stop = threading.Event()

    # ---- validation (static so UI can call without instantiating) ----
    @staticmethod
    def validate_video(path: str) -> None:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"video not found: {path}")
        if p.suffix.lower() not in _ALLOWED_EXT:
            raise ValueError(f"only MP4 supported, got: {p.suffix}")
        if p.stat().st_size < _MIN_VIDEO_BYTES:
            raise ValueError(f"video too small (<1MB): {p.stat().st_size} bytes")

    @staticmethod
    def validate_time(t: datetime | None) -> None:
        """If t is None (immediate mode), no check. Otherwise must be at
        least SCHEDULED_MIN_HOURS in the future."""
        if t is None:
            return
        from datetime import timedelta
        min_t = datetime.now() + timedelta(hours=SCHEDULED_MIN_HOURS)
        if t < min_t:
            raise ValueError(f"scheduled time must be at least {SCHEDULED_MIN_HOURS}h in the future")

    # ---- public API ----
    def submit(self, video_path: str, scheduled_time: datetime | None, group_id: int) -> int:
        """Validate and enqueue a task. scheduled_time=None means publish immediately.
        Returns task_id."""
        self.validate_video(video_path)
        self.validate_time(scheduled_time)
        active_accounts = [a for a in self._store.list_accounts(group_id=group_id) if a["is_active"] == 1]
        if not active_accounts:
            raise ValueError(f"no active accounts in group {group_id}")
        sched_str = scheduled_time.isoformat(timespec="seconds") if scheduled_time else ""
        task_id = self._store.create_task(video_path, group_id, sched_str)
        for acc in active_accounts:
            log_id = self._store.create_task_log(task_id, acc["id"])
            self._inbox.put(log_id)
        return task_id

    def retry(self, log_id: int, *, allow_submitted: bool = False, allow_incomplete: bool = False) -> bool:
        """Manually re-enqueue a task_log. Bumps attempt_count by 1 so the
        next attempt runs in headed mode (any attempt > 1 is headed).

        By default only failed logs can be retried. The history UI may pass
        allow_submitted=True after the user manually verifies that a submitted
        log is missing from the platform backend, or allow_incomplete=True to
        recover pending/uploading logs stranded by an app shutdown.
        """
        log = next((l for l in self._store.list_task_logs() if l["id"] == log_id), None)
        if log is None:
            return False
        can_retry = (
            log["status"] == "failed"
            or (allow_submitted and log["status"] == "submitted")
            or (allow_incomplete and log["status"] in {"pending", "uploading"})
        )
        if not can_retry:
            return False
        self._store.bump_attempt_and_requeue(log_id, new_attempt_count=log["attempt_count"] + 1)
        self._emit(log_id, log["account_id"], "pending")
        self._inbox.put(log_id)
        return True

    def stop(self) -> None:
        self._stop.set()
        self._inbox.put(-1)  # wake up the queue

    # ---- internals ----
    def _emit(self, log_id: int, account_id: int, status: str) -> None:
        try:
            self.status_changed.emit(log_id, account_id, status)
        except Exception:
            pass  # never let signal failures kill the worker

    def _mark_failed(self, log_id: int, account_id: int, err: str, *, retryable: bool) -> None:
        """Record a failure. If retryable AND this was the headless first
        attempt, immediately re-enqueue once in headed mode so the user can
        intervene. After the headed retry fails, the log stays failed for the
        user to manually retry."""
        self._store.update_task_log_status(log_id, "failed", error_msg=err)
        if retryable and AUTO_HEADED_RETRY:
            log = next((l for l in self._store.list_task_logs() if l["id"] == log_id), None)
            attempts = log["attempt_count"] if log else 99
            if attempts == 1:
                # Bump to attempt 2 (which is headed) and re-enqueue immediately.
                self._store.bump_attempt_and_requeue(log_id, 2)
                self._inbox.put(log_id)
                self._emit(log_id, account_id, "pending")
                return
        self._emit(log_id, account_id, "failed")

    def process_one(self, log_id: int) -> None:
        """Process a single task_log. Designed to be called in a worker
        thread; never raises (catches all exceptions and marks failed).

        Headless mode chosen by attempt_count: 1 → headless, >1 → headed.
        Setup-time errors (account/task/publisher missing) are NOT retried;
        upload-time errors (timeout / publisher returned false / unexpected
        exception) trigger one auto-retry in headed mode."""
        log = next((l for l in self._store.list_task_logs() if l["id"] == log_id), None)
        if log is None:
            return
        account = next((a for a in self._store.list_accounts() if a["id"] == log["account_id"]), None)
        if account is None:
            self._mark_failed(log_id, log["account_id"], "account not found", retryable=False)
            return
        task = next((t for t in self._store.list_tasks() if t["id"] == log["task_id"]), None)
        if task is None:
            self._mark_failed(log_id, account["id"], "task not found", retryable=False)
            return
        publisher = self._publishers.get(account["platform"])
        if publisher is None:
            self._mark_failed(log_id, account["id"], f"no publisher for {account['platform']}", retryable=False)
            return

        title = _clean_title(Path(task["video_path"]).stem)
        sched_raw = task["scheduled_time"]
        scheduled = datetime.fromisoformat(sched_raw) if sched_raw else None  # None → immediate

        headless = _headless_for_attempt(log["attempt_count"])
        timeout_sec = _TIMEOUT_HEADLESS_SEC if headless else _TIMEOUT_HEADED_SEC

        self._store.update_task_log_status(log_id, "uploading")
        self._emit(log_id, account["id"], "uploading" if headless else "uploading(有头)")

        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(
                    publisher.upload,
                    account["profile_path"],
                    task["video_path"],
                    title,
                    scheduled,
                    headless,
                )
                success, err = future.result(timeout=timeout_sec)
        except FutureTimeout:
            mode_desc = "无头" if headless else "有头"
            self._mark_failed(log_id, account["id"],
                              f"upload timeout (>{timeout_sec}s, {mode_desc})", retryable=True)
            return
        except Exception as e:  # noqa: BLE001 — catch everything so worker stays alive
            self._mark_failed(log_id, account["id"], f"{type(e).__name__}: {e}", retryable=True)
            return

        if success:
            self._store.update_task_log_status(log_id, "submitted")
            self._emit(log_id, account["id"], "submitted")
        else:
            self._mark_failed(log_id, account["id"], err or "unknown error", retryable=True)

    def _sweep_retries(self) -> int:
        """Legacy: re-enqueue failed logs whose next_retry_at has arrived.
        Kept for backward-compat with old DBs that may have next_retry_at set;
        the current auto-retry path bypasses this and re-enqueues immediately."""
        now = datetime.now().isoformat(timespec="seconds")
        due = self._store.list_task_logs_due_for_retry(now)
        for log in due:
            new_attempts = log["attempt_count"] + 1
            self._store.bump_attempt_and_requeue(log["id"], new_attempts)
            self._inbox.put(log["id"])
            self._emit(log["id"], log["account_id"], "pending")
        return len(due)

    def run(self) -> None:  # QThread entry point
        while not self._stop.is_set():
            try:
                log_id = self._inbox.get(timeout=1.0)
            except _queue.Empty:
                continue
            if log_id == -1:
                break
            try:
                self.process_one(log_id)
            except Exception:
                # Last-resort safety net; process_one already catches its own.
                traceback.print_exc()
