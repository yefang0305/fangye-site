"""Persistent local message store plus processed-set."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from publisher.message_reader import Message


class MessageStore:
    """Thread-safe message state for the message-management tab.

    Messages are cached to JSON so the message-management tab is not empty
    after restarting MediaPush. The seen-set is a lightweight processed marker.
    """

    def __init__(self, seen_path: Path | str, messages_path: Path | str | None = None):
        self._seen_path = Path(seen_path)
        self._messages_path = Path(messages_path) if messages_path else self._seen_path.with_name("message_cache.json")
        self._lock = threading.Lock()
        self._messages: dict[str, Message] = self._load_messages()
        self._busy_accounts: set[int] = set()
        self._seen: dict[str, str] = self._load_seen()

    def _load_seen(self) -> dict[str, str]:
        if not self._seen_path.exists():
            return {}
        try:
            data = json.loads(self._seen_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def _save_seen(self) -> None:
        self._seen_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._seen_path.with_suffix(self._seen_path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(self._seen, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._seen_path)

    def _load_messages(self) -> dict[str, Message]:
        if not self._messages_path.exists():
            return {}
        try:
            data = json.loads(self._messages_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, list):
            return {}
        messages: dict[str, Message] = {}
        for row in data:
            try:
                fetched_raw = str(row.get("fetched_at") or "")
                fetched_at = datetime.fromisoformat(fetched_raw) if fetched_raw else datetime.now()
                msg = Message(
                    account_id=int(row["account_id"]),
                    account_name=str(row.get("account_name") or ""),
                    conversation_id=str(row["conversation_id"]),
                    user_name=str(row.get("user_name") or ""),
                    user_avatar_url=str(row.get("user_avatar_url") or ""),
                    preview=str(row.get("preview") or ""),
                    timestamp_str=str(row.get("timestamp_str") or ""),
                    fetched_at=fetched_at,
                )
            except Exception:
                continue
            messages[msg.key] = msg
        return messages

    def _save_messages(self) -> None:
        self._messages_path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for msg in sorted(self._messages.values(), key=lambda item: item.fetched_at, reverse=True):
            rows.append(
                {
                    "account_id": msg.account_id,
                    "account_name": msg.account_name,
                    "conversation_id": msg.conversation_id,
                    "user_name": msg.user_name,
                    "user_avatar_url": msg.user_avatar_url,
                    "preview": msg.preview,
                    "timestamp_str": msg.timestamp_str,
                    "fetched_at": msg.fetched_at.isoformat(timespec="seconds"),
                }
            )
        tmp = self._messages_path.with_suffix(self._messages_path.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._messages_path)

    @staticmethod
    def _key(account_id: int, conversation_id: str) -> str:
        return f"{account_id}_{conversation_id}"

    def is_seen(self, account_id: int, conversation_id: str) -> bool:
        with self._lock:
            return self._key(account_id, conversation_id) in self._seen

    def mark_seen(self, account_id: int, conversation_id: str) -> None:
        key = self._key(account_id, conversation_id)
        with self._lock:
            self._seen[key] = datetime.now().isoformat(timespec="seconds")
            self._save_seen()
            self._save_messages()

    def remove(self, account_id: int, conversation_id: str) -> None:
        with self._lock:
            self._messages.pop(self._key(account_id, conversation_id), None)
            self._save_messages()

    def upsert(self, msg: Message) -> bool:
        """Add or update a message.

        Returns True when the row is new or its visible message content changed.
        """
        with self._lock:
            old = self._messages.get(msg.key)
            if old is not None and _same_visible_message(old, msg):
                return False
            self._messages[msg.key] = msg
            self._save_messages()
            return True

    def list_all(self) -> list[Message]:
        with self._lock:
            return sorted(
                self._messages.values(),
                key=lambda msg: msg.fetched_at,
                reverse=True,
            )

    def mark_busy(self, account_id: int) -> None:
        with self._lock:
            self._busy_accounts.add(account_id)

    def mark_idle(self, account_id: int) -> None:
        with self._lock:
            self._busy_accounts.discard(account_id)

    def is_busy(self, account_id: int) -> bool:
        with self._lock:
            return account_id in self._busy_accounts


def _same_visible_message(left: Message, right: Message) -> bool:
    return (
        left.account_name == right.account_name
        and left.user_name == right.user_name
        and left.user_avatar_url == right.user_avatar_url
        and left.preview == right.preview
        and left.timestamp_str == right.timestamp_str
    )
