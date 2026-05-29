import pytest
from datetime import datetime, timedelta
from db.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "test.db"))


def test_create_group(store):
    gid = store.create_group("group1")
    assert gid == 1
    groups = store.list_groups()
    assert len(groups) == 1
    assert groups[0]["id"] == 1
    assert groups[0]["name"] == "group1"


def test_add_account(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "天乙师兄", "/path/to/profile")
    assert aid >= 1
    accounts = store.list_accounts(group_id=gid)
    assert len(accounts) == 1
    assert accounts[0]["display_name"] == "天乙师兄"
    assert accounts[0]["platform"] == "douyin"
    assert accounts[0]["profile_path"] == "/path/to/profile"
    assert accounts[0]["is_active"] == 1


def test_list_accounts_no_filter(store):
    g1 = store.create_group("g1")
    g2 = store.create_group("g2")
    store.add_account(g1, "douyin", "a1", "/p1")
    store.add_account(g2, "douyin", "a2", "/p2")
    assert len(store.list_accounts()) == 2


def test_update_account_active(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")
    store.update_account_active(aid, 0)
    accounts = store.list_accounts()
    assert accounts[0]["is_active"] == 0


def test_create_task_and_log(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a1", "/p")
    tid = store.create_task("video.mp4", gid, "2026-04-25T17:00:00")
    assert tid >= 1
    lid = store.create_task_log(tid, aid)
    assert lid >= 1
    store.update_task_log_status(lid, "submitted", error_msg=None)
    logs = store.list_task_logs(task_id=tid)
    assert len(logs) == 1
    assert logs[0]["status"] == "submitted"
    assert logs[0]["account_id"] == aid


def test_update_task_log_status_with_error(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")
    tid = store.create_task("v.mp4", gid, "2026-04-25T17:00:00")
    lid = store.create_task_log(tid, aid)
    store.update_task_log_status(lid, "failed", error_msg="upload timeout")
    logs = store.list_task_logs(task_id=tid)
    assert logs[0]["status"] == "failed"
    assert logs[0]["error_msg"] == "upload timeout"


def test_list_tasks_filter_by_status(store):
    gid = store.create_group("g")
    t1 = store.create_task("v1.mp4", gid, "2026-04-25T17:00:00")
    t2 = store.create_task("v2.mp4", gid, "2026-04-25T17:00:00")
    store.update_task_status(t1, "done")
    pending = store.list_tasks(status="pending")
    assert len(pending) == 1
    assert pending[0]["id"] == t2


def test_rename_group(store):
    gid = store.create_group("old")
    store.rename_group(gid, "new")
    assert store.list_groups()[0]["name"] == "new"


def test_delete_group_empty(store):
    gid = store.create_group("g")
    store.delete_group(gid)
    assert store.list_groups() == []


def test_delete_group_with_accounts_fails(store):
    gid = store.create_group("g")
    store.add_account(gid, "douyin", "a", "/p")
    with pytest.raises(ValueError, match="still has accounts"):
        store.delete_group(gid)


def test_move_account_to_group(store):
    g1 = store.create_group("g1")
    g2 = store.create_group("g2")
    aid = store.add_account(g1, "douyin", "a", "/p")
    store.move_account_to_group(aid, g2)
    assert store.list_accounts(group_id=g2)[0]["id"] == aid
    assert store.list_accounts(group_id=g1) == []


def test_update_account_display_name(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "old", "/p")
    store.update_account_display_name(aid, "new")
    assert store.list_accounts()[0]["display_name"] == "new"


def test_task_log_default_attempt_count(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")
    tid = store.create_task("v.mp4", gid, "")
    lid = store.create_task_log(tid, aid)
    log = store.list_task_logs(task_id=tid)[0]
    assert log["attempt_count"] == 1
    assert log["next_retry_at"] is None


def test_update_task_log_for_retry_sets_next_retry_at(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")
    tid = store.create_task("v.mp4", gid, "")
    lid = store.create_task_log(tid, aid)
    next_at = "2026-05-01T12:00:00"
    store.update_task_log_for_retry(lid, next_at)
    log = store.list_task_logs(task_id=tid)[0]
    assert log["next_retry_at"] == next_at


def test_list_task_logs_due_for_retry(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")
    tid = store.create_task("v.mp4", gid, "")
    l_due = store.create_task_log(tid, aid)
    l_future = store.create_task_log(tid, aid)
    l_no_retry = store.create_task_log(tid, aid)
    # Mark all three as failed first (only failed logs are eligible for retry)
    for lid in (l_due, l_future, l_no_retry):
        store.update_task_log_status(lid, "failed", error_msg="x")
    store.update_task_log_for_retry(l_due, "2026-04-01T00:00:00")    # past
    store.update_task_log_for_retry(l_future, "2099-01-01T00:00:00")  # far future
    # l_no_retry: no next_retry_at set → not eligible
    due = store.list_task_logs_due_for_retry("2026-05-01T00:00:00")
    due_ids = {l["id"] for l in due}
    assert l_due in due_ids
    assert l_future not in due_ids
    assert l_no_retry not in due_ids


def test_bump_attempt_and_requeue_resets_status(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")
    tid = store.create_task("v.mp4", gid, "")
    lid = store.create_task_log(tid, aid)
    store.update_task_log_status(lid, "failed", error_msg="boom")
    store.update_task_log_for_retry(lid, "2026-04-01T00:00:00")
    store.bump_attempt_and_requeue(lid, 2)
    log = store.list_task_logs(task_id=tid)[0]
    assert log["status"] == "pending"
    assert log["attempt_count"] == 2
    assert log["error_msg"] is None
    assert log["next_retry_at"] is None


def test_delete_task_logs_removes_orphan_tasks_only(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")

    task_one = store.create_task("one.mp4", gid, "")
    task_one_log = store.create_task_log(task_one, aid)

    task_two = store.create_task("two.mp4", gid, "")
    keep_log = store.create_task_log(task_two, aid)
    delete_log = store.create_task_log(task_two, aid)

    result = store.delete_task_logs([task_one_log, delete_log])

    assert result == {"task_logs": 2, "tasks": 1}
    logs = store.list_task_logs()
    assert {log["id"] for log in logs} == {keep_log}
    assert {task["id"] for task in store.list_tasks()} == {task_two}
    assert store.list_accounts()[0]["id"] == aid


def test_purge_submitted_history_before_keeps_actionable_and_current_rows(store):
    gid = store.create_group("g")
    aid = store.add_account(gid, "douyin", "a", "/p")

    old_submitted = store.create_task("old.mp4", gid, "2026-05-14T12:00:00")
    old_submitted_log = store.create_task_log(old_submitted, aid)
    store.update_task_log_status(old_submitted_log, "submitted")

    today_submitted = store.create_task("today.mp4", gid, "2026-05-15T07:00:00")
    today_submitted_log = store.create_task_log(today_submitted, aid)
    store.update_task_log_status(today_submitted_log, "submitted")

    future_submitted = store.create_task("future.mp4", gid, "2026-05-16T07:00:00")
    future_submitted_log = store.create_task_log(future_submitted, aid)
    store.update_task_log_status(future_submitted_log, "submitted")

    old_failed = store.create_task("old-failed.mp4", gid, "2026-05-14T18:00:00")
    old_failed_log = store.create_task_log(old_failed, aid)
    store.update_task_log_status(old_failed_log, "failed", error_msg="needs retry")

    result = store.purge_submitted_history_before("2026-05-15")

    assert result == {"task_logs": 1, "tasks": 1}
    remaining_logs = {log["id"]: log for log in store.list_task_logs()}
    assert old_submitted_log not in remaining_logs
    assert today_submitted_log in remaining_logs
    assert future_submitted_log in remaining_logs
    assert old_failed_log in remaining_logs

    remaining_tasks = {task["id"] for task in store.list_tasks()}
    assert old_submitted not in remaining_tasks
    assert old_failed in remaining_tasks


def test_schema_migration_adds_columns_to_old_db(tmp_path):
    """Simulate an old DB without attempt_count/next_retry_at columns and
    confirm Store() upgrades it in place."""
    import sqlite3
    db_path = str(tmp_path / "old.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE groups (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE accounts (id INTEGER PRIMARY KEY, group_id INTEGER, platform TEXT, display_name TEXT, profile_path TEXT, is_active INTEGER DEFAULT 1);
        CREATE TABLE tasks (id INTEGER PRIMARY KEY, video_path TEXT, group_id INTEGER, scheduled_time TEXT, status TEXT DEFAULT 'pending', created_at TEXT);
        CREATE TABLE task_logs (id INTEGER PRIMARY KEY, task_id INTEGER, account_id INTEGER, status TEXT DEFAULT 'pending', error_msg TEXT, submitted_at TEXT);
        INSERT INTO groups (name, created_at) VALUES ('g', '2026-01-01');
        INSERT INTO accounts (group_id, platform, display_name, profile_path) VALUES (1, 'douyin', 'a', '/p');
        INSERT INTO tasks (video_path, group_id, scheduled_time, created_at) VALUES ('v.mp4', 1, '', '2026-01-01');
        INSERT INTO task_logs (task_id, account_id) VALUES (1, 1);
    """)
    conn.commit()
    conn.close()
    # Now open with our Store — should auto-migrate
    s = Store(db_path)
    log = s.list_task_logs()[0]
    assert log["attempt_count"] == 1   # migration default
    assert log["next_retry_at"] is None


def test_persistence_across_instances(tmp_path):
    db_path = str(tmp_path / "p.db")
    s1 = Store(db_path)
    gid = s1.create_group("persistent")
    s1.close()
    s2 = Store(db_path)
    assert s2.list_groups()[0]["name"] == "persistent"
