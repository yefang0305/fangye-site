from datetime import datetime, timedelta
import pytest

from db.store import Store
from publisher.base import Publisher
from publisher.queue import PublishQueue


class MockPublisher(Publisher):
    platform = "douyin"

    def __init__(self, success: bool = True, error: str = ""):
        self.success = success
        self.error = error
        self.calls: list[tuple] = []

    def check_login(self, profile_path: str) -> bool:
        return True

    def detect_account_name(self, profile_path: str) -> str:
        return ""

    def upload(self, profile_path, video_path, title, scheduled_time, headless=True):
        self.calls.append((profile_path, video_path, title, scheduled_time, headless))
        return (self.success, self.error)


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "test.db"))


@pytest.fixture
def queue(store):
    return PublishQueue(store, publishers={"douyin": MockPublisher()})


def test_validate_video_rejects_missing_file(queue):
    with pytest.raises(FileNotFoundError):
        queue.validate_video("nonexistent.mp4")


def test_validate_video_rejects_non_mp4(tmp_path, queue):
    f = tmp_path / "x.mov"
    f.write_bytes(b"x" * 2_000_000)
    with pytest.raises(ValueError, match="MP4"):
        queue.validate_video(str(f))


def test_validate_video_rejects_too_small(tmp_path, queue):
    f = tmp_path / "x.mp4"
    f.write_bytes(b"x" * 100)
    with pytest.raises(ValueError, match="too small"):
        queue.validate_video(str(f))


def test_validate_video_accepts_valid(tmp_path, queue):
    f = tmp_path / "ok.mp4"
    f.write_bytes(b"x" * 2_000_000)
    queue.validate_video(str(f))  # should not raise


def test_validate_time_rejects_under_2h(queue):
    soon = datetime.now() + timedelta(minutes=30)
    with pytest.raises(ValueError, match="2h"):
        queue.validate_time(soon)


def test_validate_time_accepts_3h_future(queue):
    future = datetime.now() + timedelta(hours=3)
    queue.validate_time(future)


def test_validate_time_none_means_immediate(queue):
    queue.validate_time(None)  # immediate mode bypasses time check


def test_submit_creates_task_and_logs(tmp_path, store):
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a1", "/p")
    store.add_account(gid, "douyin", "a2", "/p2")
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    q = PublishQueue(store, publishers={"douyin": MockPublisher()})
    tid = q.submit(str(f), future, gid)
    logs = store.list_task_logs(task_id=tid)
    assert len(logs) == 2  # 一个组2个active账号 → 2条日志


def test_submit_skips_inactive_accounts(tmp_path, store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a1", "/p")
    store.update_account_active(aid, 0)
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    q = PublishQueue(store, publishers={"douyin": MockPublisher()})
    with pytest.raises(ValueError, match="no active"):
        q.submit(str(f), future, gid)


def test_submit_rejects_invalid_video(tmp_path, store):
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    q = PublishQueue(store, publishers={"douyin": MockPublisher()})
    future = datetime.now() + timedelta(hours=3)
    with pytest.raises(FileNotFoundError):
        q.submit("nonexistent.mp4", future, gid)


def test_process_one_marks_submitted_on_success(tmp_path, store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"
    f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    pub = MockPublisher(success=True)
    q = PublishQueue(store, publishers={"douyin": pub})
    tid = q.submit(str(f), future, gid)
    log_id = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(log_id)
    assert store.list_task_logs(task_id=tid)[0]["status"] == "submitted"
    assert len(pub.calls) == 1


def test_process_one_first_fail_triggers_headed_auto_retry(tmp_path, store):
    """1st attempt fails → auto re-enqueued for attempt 2 (headed). Status
    reflects 'pending' (waiting for the retry), not 'failed'."""
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    pub = MockPublisher(success=False, error="网络超时")
    q = PublishQueue(store, publishers={"douyin": pub})
    tid = q.submit(str(f), future, gid)
    log_id = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(log_id)
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "pending"          # auto-retry queued
    assert log["attempt_count"] == 2           # bumped
    # And the log_id was put back in the inbox
    assert q._inbox.get_nowait() == log_id


def test_process_one_second_fail_stays_failed(tmp_path, store):
    """When attempt 2 (headed) also fails, the log stays 'failed' — no further
    auto-retry, user must manually retry."""
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    pub = MockPublisher(success=False, error="网络超时")
    q = PublishQueue(store, publishers={"douyin": pub})
    tid = q.submit(str(f), future, gid)
    lid = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(lid)                          # 1st (headless) fail → auto-retry enqueued
    q._inbox.get_nowait()                       # drain auto-retry from inbox
    q.process_one(lid)                          # 2nd (headed) fail
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "failed"
    assert log["attempt_count"] == 2
    assert pub.calls[0][-1] is True             # 1st call: headless=True
    assert pub.calls[1][-1] is False            # 2nd call: headless=False (auto-retry)


def test_process_one_marks_failed_on_exception(tmp_path, store):
    """An exception in the publisher is treated like a transient failure:
    attempt 1 → auto-retry; attempt 2 → final failed."""
    class BoomPublisher(Publisher):
        platform = "douyin"
        def check_login(self, profile_path): return True
        def detect_account_name(self, profile_path): return ""
        def upload(self, *args, **kwargs):
            raise RuntimeError("浏览器崩溃")

    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    q = PublishQueue(store, publishers={"douyin": BoomPublisher()})
    tid = q.submit(str(f), future, gid)
    log_id = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(log_id)                  # 1st: exception → auto-retry queued
    q._inbox.get_nowait()
    q.process_one(log_id)                  # 2nd: exception → stays failed
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "failed"
    assert "浏览器崩溃" in log["error_msg"]
    assert log["attempt_count"] == 2


# ---- auto-retry behavior (T3/T4) ----

class FlakyPublisher(Publisher):
    """Returns failure for the first `fail_times` calls, then success."""
    platform = "douyin"

    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    def check_login(self, profile_path): return True
    def detect_account_name(self, profile_path): return ""

    def upload(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            return (False, f"flake#{self.calls}")
        return (True, "")


def test_headed_auto_retry_succeeds(tmp_path, store):
    """1st attempt headless fails (e.g. captcha), auto-retry headed succeeds."""
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    pub = FlakyPublisher(fail_times=1)
    q = PublishQueue(store, publishers={"douyin": pub})
    tid = q.submit(str(f), future, gid)
    lid = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(lid)                     # 1st: headless fail → re-enqueued
    requeued = q._inbox.get_nowait()
    assert requeued == lid
    q.process_one(lid)                     # 2nd: headed succeeds
    final = store.list_task_logs(task_id=tid)[0]
    assert final["status"] == "submitted"
    assert final["attempt_count"] == 2
    assert pub.calls == 2


def test_setup_errors_not_retryable(tmp_path, store):
    """Missing-publisher should NOT schedule retries (permanent error)."""
    gid = store.create_group("g")
    # Account on platform 'mystery' for which no publisher is registered
    store.add_account(gid, "mystery", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    q = PublishQueue(store, publishers={"douyin": MockPublisher()})
    tid = q.submit(str(f), future, gid)
    lid = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(lid)
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "failed"
    assert log["next_retry_at"] is None
    assert "no publisher" in log["error_msg"]


def test_manual_retry_bumps_attempt_count(tmp_path, store):
    """Manual retry from UI bumps attempt_count by 1 so the next attempt
    runs in headed mode (any attempt > 1 is headed)."""
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    pub = FlakyPublisher(fail_times=10)  # always fails
    q = PublishQueue(store, publishers={"douyin": pub})
    tid = q.submit(str(f), future, gid)
    lid = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(lid)                       # 1st (headless) fail → auto-retry queued
    q._inbox.get_nowait()                    # drain
    q.process_one(lid)                       # 2nd (headed) fail → final failed
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "failed"
    assert log["attempt_count"] == 2
    # Now user clicks manual retry → attempt_count → 3 (still headed)
    assert q.retry(lid) is True
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "pending"
    assert log["attempt_count"] == 3
    # Process the retry → fails again, no further auto-retry (only attempt 1 triggers it)
    q._inbox.get_nowait()
    q.process_one(lid)
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "failed"
    assert log["attempt_count"] == 3
    # Manual retry can be repeated indefinitely
    assert q.retry(lid) is True
    log = store.list_task_logs(task_id=tid)[0]
    assert log["attempt_count"] == 4


def test_manual_retry_submitted_requires_explicit_allow(tmp_path, store):
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    q = PublishQueue(store, publishers={"douyin": MockPublisher()})
    tid = q.submit(str(f), future, gid)
    lid = store.list_task_logs(task_id=tid)[0]["id"]
    store.update_task_log_status(lid, "submitted")

    assert q.retry(lid) is False
    assert q.retry(lid, allow_submitted=True) is True

    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "pending"
    assert log["attempt_count"] == 2
    assert q._inbox.get_nowait() == lid


@pytest.mark.parametrize("status", ["pending", "uploading"])
def test_manual_retry_incomplete_requires_explicit_allow(tmp_path, store, status):
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    q = PublishQueue(store, publishers={"douyin": MockPublisher()})
    tid = q.submit(str(f), future, gid)
    lid = store.list_task_logs(task_id=tid)[0]["id"]
    store.update_task_log_status(lid, status)

    assert q.retry(lid) is False
    assert q.retry(lid, allow_incomplete=True) is True

    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "pending"
    assert log["attempt_count"] == 2
    assert q._inbox.get_nowait() == lid


def test_headless_mode_chosen_per_attempt(tmp_path, store):
    """Verify the publisher receives headless=True on attempt 1, False on >1."""
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    f = tmp_path / "v.mp4"; f.write_bytes(b"x" * 2_000_000)
    future = datetime.now() + timedelta(hours=3)
    pub = MockPublisher(success=False, error="boom")
    q = PublishQueue(store, publishers={"douyin": pub})
    tid = q.submit(str(f), future, gid)
    lid = store.list_task_logs(task_id=tid)[0]["id"]
    q.process_one(lid)                       # attempt 1 → headless
    q._inbox.get_nowait()
    q.process_one(lid)                       # attempt 2 → headed
    # MockPublisher.calls signature: (profile_path, video_path, title, scheduled_time, headless)
    headless_flags = [c[-1] for c in pub.calls]
    assert headless_flags == [True, False]
