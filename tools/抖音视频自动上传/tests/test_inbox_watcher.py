"""Tests for the inbox watcher."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from db.store import Store
from publisher.inbox_watcher import InboxWatcher


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "test.db"))


class FakeQueue:
    """Stands in for PublishQueue in tests — collects submit() calls."""

    def __init__(self):
        self.submitted: list[tuple] = []
        self._next_task_id = 100

    def submit(self, video_path: str, scheduled_time, group_id: int) -> int:
        self.submitted.append((video_path, scheduled_time, group_id))
        tid = self._next_task_id
        self._next_task_id += 1
        return tid


def _make_batch(inbox: Path, batch_name: str, video_names: list[str], scheduled_time: str) -> Path:
    bdir = inbox / batch_name
    bdir.mkdir(parents=True)
    for name in video_names:
        (bdir / name).write_bytes(b"x" * 2_000_000)
    manifest = {
        "version": 1,
        "batch_id": batch_name,
        "scheduled_time": scheduled_time,
        "videos": video_names,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": "test",
    }
    (bdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return bdir


def _seed_groups(store, n: int) -> list[int]:
    """Create n groups, each with one active douyin account."""
    ids = []
    for i in range(n):
        gid = store.create_group(f"g{i}")
        store.add_account(gid, "douyin", f"a{i}", f"/p{i}")
        ids.append(gid)
    return ids


def test_dispatches_videos_to_random_groups(tmp_path, store):
    _seed_groups(store, 3)
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    bdir = _make_batch(inbox, "20260427-070000-morning",
                       ["v1.mp4", "v2.mp4", "v3.mp4"],
                       "2026-04-27T07:00:00")
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed))

    n = w.process_once()
    assert n == 1
    assert len(fake_q.submitted) == 3
    # All 3 groups got exactly one video each (random pairing, no duplicates)
    assigned_groups = sorted(g for *_, g in fake_q.submitted)
    assert assigned_groups == [1, 2, 3]
    # Batch directory moved out of inbox into processed/
    assert not bdir.exists()
    moved = processed / "20260427-070000-morning"
    assert moved.is_dir()
    assert (moved / "result.json").is_file()
    assert (moved / "manifest.json").is_file()
    # Videos came along
    for n in ["v1.mp4", "v2.mp4", "v3.mp4"]:
        assert (moved / n).is_file()


def test_skips_when_not_enough_active_groups(tmp_path, store):
    _seed_groups(store, 1)  # only 1 group, need 3
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    bdir = _make_batch(inbox, "batch-x", ["v1.mp4", "v2.mp4", "v3.mp4"], "2026-04-27T07:00:00")
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed))

    n = w.process_once()
    assert n == 0  # nothing successfully processed
    assert len(fake_q.submitted) == 0
    # Batch stays in place (not moved)
    assert bdir.exists()
    # Error log written
    assert (bdir / "error.log").is_file()
    assert "not enough active groups" in (bdir / "error.log").read_text(encoding="utf-8")
    # Marker cleaned up so next tick will retry
    assert not (bdir / ".processing").exists()


def test_skips_groups_with_only_inactive_accounts(tmp_path, store):
    """A group with all accounts is_active=0 should not count toward the pool."""
    g_active = store.create_group("active")
    store.add_account(g_active, "douyin", "a", "/p")
    g_inactive = store.create_group("inactive")
    inactive_aid = store.add_account(g_inactive, "douyin", "b", "/p2")
    store.update_account_active(inactive_aid, 0)

    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    _make_batch(inbox, "b", ["v1.mp4", "v2.mp4"], "2026-04-27T07:00:00")
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed))
    n = w.process_once()
    # only 1 active group, need 2 → should not process
    assert n == 0
    assert len(fake_q.submitted) == 0


def test_already_processed_marker_skipped(tmp_path, store):
    _seed_groups(store, 2)
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    bdir = _make_batch(inbox, "b", ["v1.mp4", "v2.mp4"], "2026-04-27T07:00:00")
    (bdir / ".processing").touch()  # claim
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed))
    n = w.process_once()
    assert n == 0
    assert len(fake_q.submitted) == 0


def test_video_path_in_db_updated_after_move(tmp_path, store):
    """After move, the queue's submit was called with the inbox path, but
    the watcher then patches DB to point at the processed/ location so the
    upload worker can find the file."""
    _seed_groups(store, 1)
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    _make_batch(inbox, "b", ["v.mp4"], "2026-04-27T07:00:00")

    class RealishQueue(FakeQueue):
        """Mimics PublishQueue: actually writes a task row so we can inspect."""
        def __init__(self, store):
            super().__init__()
            self.store = store

        def submit(self, video_path, scheduled_time, group_id):
            tid = self.store.create_task(video_path, group_id, scheduled_time.isoformat(timespec="seconds"))
            self.submitted.append((video_path, scheduled_time, group_id))
            return tid

    q = RealishQueue(store)
    w = InboxWatcher(store, q, str(inbox), str(processed))
    w.process_once()
    tasks = store.list_tasks()
    assert len(tasks) == 1
    # video_path in DB should point at processed/, not inbox/
    assert "processed" in tasks[0]["video_path"].lower().replace("\\", "/")
    # And the file actually exists at that path
    assert Path(tasks[0]["video_path"]).is_file()


def test_repeat_errors_are_deduped(tmp_path, store):
    """Same error on the next tick should NOT re-log the full traceback;
    only the first occurrence + threshold milestones get a log line."""
    _seed_groups(store, 1)  # only 1 group, need 3 → persistent failure
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    bdir = _make_batch(inbox, "b", ["v1.mp4", "v2.mp4", "v3.mp4"], "2026-04-27T07:00:00")
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed), poll_sec=0.01)
    # First call → full error logged + state recorded
    w.process_once()
    log_after_1 = (bdir / "error.log").read_text(encoding="utf-8")
    assert log_after_1.count("not enough active groups") >= 1
    # Bypass backoff: clear next_attempt_ts so the second call actually retries
    w._error_state["b"]["next_attempt_ts"] = 0
    # Same error on next tick → state.count incremented but NOT logged
    # (count goes 1 → 2, neither hits a milestone)
    w.process_once()
    log_after_2 = (bdir / "error.log").read_text(encoding="utf-8")
    assert log_after_2 == log_after_1, "duplicate error should not re-log"
    assert w._error_state["b"]["count"] == 2


def test_backoff_skips_batch_until_next_attempt(tmp_path, store):
    """Once a batch is in backoff, process_once should leave it alone."""
    _seed_groups(store, 1)
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    _make_batch(inbox, "b", ["v1.mp4", "v2.mp4"], "2026-04-27T07:00:00")
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed), poll_sec=0.01)
    w.process_once()  # record error
    # Pretend backoff is far in the future
    import time as _t
    w._error_state["b"]["next_attempt_ts"] = _t.time() + 9999
    initial_log_size = (inbox / "b" / "error.log").stat().st_size
    w.process_once()  # should be a no-op for batch "b"
    assert (inbox / "b" / "error.log").stat().st_size == initial_log_size


def test_state_cleared_when_batch_disappears(tmp_path, store):
    """If user manually deletes a stuck batch, watcher state should clean up."""
    _seed_groups(store, 1)
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    bdir = _make_batch(inbox, "b", ["v1.mp4", "v2.mp4"], "2026-04-27T07:00:00")
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed), poll_sec=0.01)
    w.process_once()
    assert "b" in w._error_state
    # User deletes the batch
    import shutil as _shutil
    _shutil.rmtree(bdir)
    w.process_once()
    assert "b" not in w._error_state


def test_malformed_manifest_writes_error_and_unblocks(tmp_path, store):
    _seed_groups(store, 2)
    inbox = tmp_path / "inbox"
    processed = tmp_path / "processed"
    bdir = inbox / "b"
    bdir.mkdir(parents=True)
    (bdir / "manifest.json").write_text("not valid json", encoding="utf-8")
    fake_q = FakeQueue()
    w = InboxWatcher(store, fake_q, str(inbox), str(processed))
    w.process_once()
    assert (bdir / "error.log").is_file()
    assert not (bdir / ".processing").exists()
