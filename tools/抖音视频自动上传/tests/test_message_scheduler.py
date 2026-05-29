from datetime import datetime

import pytest

from db.store import Store
from publisher.message_reader import Message, MessageReader
from publisher.message_scheduler import MessageScheduler, should_trigger_interval
from publisher.message_store import MessageStore


class MockReader(MessageReader):
    platform = "douyin"

    def __init__(self, messages_by_account=None, fail=False):
        self.messages_by_account = messages_by_account or {}
        self.fail = fail
        self.calls: list[tuple[int, str, str]] = []

    def fetch_unread_strangers(self, account_id, account_name, profile_path):
        self.calls.append((account_id, account_name, profile_path))
        if self.fail:
            raise RuntimeError("fetch failed")
        return self.messages_by_account.get(account_id, [])

    def reply(self, profile_path, conversation_id, text):
        return (True, "")

    def fetch_conversation_messages(self, profile_path, conversation_id):
        return []


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "test.db"))


@pytest.fixture
def msg_store(tmp_path):
    return MessageStore(tmp_path / "seen.json")


def _msg(account_id=1, conv="c1", text="hello"):
    return Message(
        account_id=account_id,
        account_name=f"acc{account_id}",
        conversation_id=conv,
        user_name="user",
        user_avatar_url="",
        preview=text,
        timestamp_str="09:00",
    )


def _add_account(store, group_id, name, platform="douyin", active=1):
    aid = store.add_account(group_id, platform, name, f"/profiles/{name}")
    store.update_account_active(aid, active)
    return aid


def _scheduler(store, msg_store, readers):
    return MessageScheduler(store, msg_store, readers, delay_range=(0, 0))


def test_run_one_round_fetches_active_douyin_accounts(store, msg_store):
    gid = store.create_group("g")
    a1 = _add_account(store, gid, "a1")
    a2 = _add_account(store, gid, "a2")
    _add_account(store, gid, "inactive", active=0)
    _add_account(store, gid, "xhs", platform="xiaohongshu")
    reader = MockReader({a1: [_msg(a1, "c1")], a2: [_msg(a2, "c2")]})

    count = _scheduler(store, msg_store, {"douyin": reader}).run_one_round()

    assert count == 2
    assert [call[0] for call in reader.calls] == [a1, a2]
    assert {m.conversation_id for m in msg_store.list_all()} == {"c1", "c2"}


def test_run_one_round_can_filter_single_account(store, msg_store):
    gid = store.create_group("g")
    a1 = _add_account(store, gid, "a1")
    a2 = _add_account(store, gid, "a2")
    reader = MockReader({a1: [_msg(a1, "c1")], a2: [_msg(a2, "c2")]})

    count = _scheduler(store, msg_store, {"douyin": reader}).run_one_round(only_account_id=a2)

    assert count == 1
    assert [call[0] for call in reader.calls] == [a2]
    assert msg_store.list_all()[0].conversation_id == "c2"


def test_run_one_round_skips_busy_accounts(store, msg_store):
    gid = store.create_group("g")
    a1 = _add_account(store, gid, "a1")
    a2 = _add_account(store, gid, "a2")
    msg_store.mark_busy(a1)
    reader = MockReader({a1: [_msg(a1, "c1")], a2: [_msg(a2, "c2")]})

    count = _scheduler(store, msg_store, {"douyin": reader}).run_one_round()

    assert count == 1
    assert [call[0] for call in reader.calls] == [a2]


def test_run_one_round_updates_processed_messages(store, msg_store):
    gid = store.create_group("g")
    a1 = _add_account(store, gid, "a1")
    msg_store.mark_seen(a1, "c1")
    reader = MockReader({a1: [_msg(a1, "c1")]})

    count = _scheduler(store, msg_store, {"douyin": reader}).run_one_round()

    assert count == 1
    assert msg_store.list_all()[0].conversation_id == "c1"


def test_run_one_round_continues_after_reader_error(store, msg_store):
    gid = store.create_group("g")
    a1 = _add_account(store, gid, "a1")
    reader = MockReader(fail=True)

    count = _scheduler(store, msg_store, {"douyin": reader}).run_one_round()

    assert count == 0
    assert [call[0] for call in reader.calls] == [a1]


def test_run_one_round_skips_missing_reader(store, msg_store):
    gid = store.create_group("g")
    _add_account(store, gid, "a1", platform="unknown")

    count = _scheduler(store, msg_store, {"douyin": MockReader()}).run_one_round()

    assert count == 0


def test_should_trigger_interval_when_elapsed():
    last = datetime(2026, 4, 29, 9, 0)
    now = datetime(2026, 4, 29, 10, 0)
    assert should_trigger_interval(last, now, 3600) is True


def test_should_not_trigger_before_interval_elapsed():
    assert should_trigger_interval(datetime(2026, 4, 29, 9, 0), datetime(2026, 4, 29, 9, 59), 3600) is False
    assert should_trigger_interval(None, datetime(2026, 4, 29, 10, 0), 3600) is False
