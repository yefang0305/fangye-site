import json
from datetime import datetime, timedelta

import pytest

from publisher.message_reader import Message
from publisher.message_store import MessageStore


def _msg(aid=1, conv="c1", name="user1", preview="hi"):
    return Message(
        account_id=aid,
        account_name=f"acc{aid}",
        conversation_id=conv,
        user_name=name,
        user_avatar_url="",
        preview=preview,
        timestamp_str="14:00",
    )


@pytest.fixture
def store(tmp_path):
    return MessageStore(seen_path=tmp_path / "seen.json")


def test_upsert_returns_true_for_new_unseen(store):
    assert store.upsert(_msg()) is True
    assert len(store.list_all()) == 1


def test_upsert_still_keeps_processed_messages_visible(store):
    m = _msg()
    store.mark_seen(m.account_id, m.conversation_id)
    assert store.upsert(m) is True
    assert store.list_all()[0].conversation_id == m.conversation_id


def test_upsert_dedups_same_conversation(store):
    store.upsert(_msg(preview="old"))
    store.upsert(_msg(preview="new"))
    items = store.list_all()
    assert len(items) == 1
    assert items[0].preview == "new"


def test_mark_seen_keeps_message_in_list(store):
    m = _msg()
    store.upsert(m)
    store.mark_seen(m.account_id, m.conversation_id)
    assert store.list_all()[0].conversation_id == m.conversation_id


def test_remove_only_drops_from_memory(store):
    m = _msg()
    store.upsert(m)
    store.remove(m.account_id, m.conversation_id)
    assert store.list_all() == []
    assert store.is_seen(m.account_id, m.conversation_id) is False


def test_seen_persists_to_json(tmp_path):
    seen = tmp_path / "seen.json"
    s1 = MessageStore(seen_path=seen)
    s1.mark_seen(1, "conv_x")
    s2 = MessageStore(seen_path=seen)
    assert s2.is_seen(1, "conv_x") is True


def test_messages_persist_to_json(tmp_path):
    seen = tmp_path / "seen.json"
    s1 = MessageStore(seen_path=seen)
    msg = _msg(aid=2, conv="conv_x", name="张三", preview="你好")
    s1.upsert(msg)
    s2 = MessageStore(seen_path=seen)
    out = s2.list_all()
    assert len(out) == 1
    assert out[0].account_id == 2
    assert out[0].user_name == "张三"
    assert out[0].preview == "你好"


def test_bad_message_cache_is_ignored(tmp_path):
    seen = tmp_path / "seen.json"
    (tmp_path / "message_cache.json").write_text("{bad json", encoding="utf-8")
    s = MessageStore(seen_path=seen)
    assert s.list_all() == []


def test_seen_loads_existing_json(tmp_path):
    seen = tmp_path / "seen.json"
    seen.write_text(json.dumps({"1_conv_y": "2026-04-28T12:00:00"}), encoding="utf-8")
    s = MessageStore(seen_path=seen)
    assert s.is_seen(1, "conv_y") is True


def test_bad_seen_json_is_ignored(tmp_path):
    seen = tmp_path / "seen.json"
    seen.write_text("{bad json", encoding="utf-8")
    s = MessageStore(seen_path=seen)
    assert s.is_seen(1, "conv_y") is False


def test_busy_account_tracking(store):
    assert store.is_busy(1) is False
    store.mark_busy(1)
    assert store.is_busy(1) is True
    store.mark_idle(1)
    assert store.is_busy(1) is False


def test_list_all_sorted_by_fetched_desc(store):
    now = datetime.now()
    m1 = _msg(conv="a")
    m1.fetched_at = now - timedelta(seconds=10)
    m2 = _msg(conv="b")
    m2.fetched_at = now
    store.upsert(m1)
    store.upsert(m2)
    out = store.list_all()
    assert [m.conversation_id for m in out] == ["b", "a"]


def test_upsert_unchanged_message_does_not_bump_order(store):
    now = datetime.now()
    old = _msg(conv="a", preview="same")
    old.fetched_at = now - timedelta(seconds=10)
    newer = _msg(conv="b", preview="newer")
    newer.fetched_at = now
    unchanged = _msg(conv="a", preview="same")
    unchanged.fetched_at = now + timedelta(seconds=10)
    store.upsert(old)
    store.upsert(newer)
    assert store.upsert(unchanged) is False
    assert [m.conversation_id for m in store.list_all()] == ["b", "a"]


def test_message_key_property():
    assert _msg(aid=12, conv="abc").key == "12_abc"
