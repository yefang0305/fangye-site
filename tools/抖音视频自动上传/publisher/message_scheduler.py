"""Background scheduler for message polling."""
from __future__ import annotations

import random
import threading
import traceback
from datetime import datetime, timedelta

from PyQt5.QtCore import QThread, pyqtSignal

from db.store import Store
from publisher.message_reader import MessageReader
from publisher.message_store import MessageStore


DEFAULT_POLL_INTERVAL_SECONDS = 60 * 60
INTER_ACCOUNT_DELAY_RANGE = (3.0, 8.0)


def should_trigger_interval(
    last_run: datetime | None,
    now: datetime,
    interval_seconds: int,
) -> bool:
    """Return True when interval_seconds elapsed since last_run."""
    if last_run is None:
        return False
    return now - last_run >= timedelta(seconds=interval_seconds)


class MessageScheduler(QThread):
    new_messages = pyqtSignal(int)
    refresh_done = pyqtSignal()
    account_status = pyqtSignal(int, str)

    def __init__(
        self,
        store: Store,
        msg_store: MessageStore,
        readers: dict[str, MessageReader],
        poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
        delay_range: tuple[float, float] = INTER_ACCOUNT_DELAY_RANGE,
    ):
        super().__init__()
        self._store = store
        self._msg_store = msg_store
        self._readers = readers
        self._poll_interval_seconds = poll_interval_seconds
        self._delay_range = delay_range
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._pending_account_id: int | None = None
        self._last_run: datetime | None = None
        self._pending_lock = threading.Lock()

    def trigger_now(self, account_id: int | None = None) -> None:
        with self._pending_lock:
            self._pending_account_id = account_id
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def run_one_round(self, only_account_id: int | None = None) -> int:
        """Synchronously fetch one polling round. Returns newly added count."""
        accounts = [
            account
            for account in self._store.list_accounts()
            if account["is_active"] == 1
        ]
        if only_account_id is not None:
            accounts = [account for account in accounts if account["id"] == only_account_id]

        new_total = 0
        for index, account in enumerate(accounts):
            if self._stop.is_set():
                break
            reader = self._readers.get(account["platform"])
            if reader is None:
                continue
            account_id = account["id"]
            if self._msg_store.is_busy(account_id):
                continue

            self._emit_status(account_id, "fetching")
            try:
                messages = reader.fetch_unread_strangers(
                    account_id,
                    account["display_name"],
                    account["profile_path"],
                )
                for message in messages:
                    if self._msg_store.upsert(message):
                        new_total += 1
                self._emit_status(account_id, "idle")
            except Exception:
                traceback.print_exc()
                self._emit_status(account_id, "error")

            if index < len(accounts) - 1:
                delay = random.uniform(*self._delay_range)
                if delay > 0 and self._stop.wait(timeout=delay):
                    break

        self._last_run = datetime.now()
        return new_total

    def _emit_status(self, account_id: int, status: str) -> None:
        try:
            self.account_status.emit(account_id, status)
        except Exception:
            pass

    def _emit_round_done(self, new_count: int) -> None:
        try:
            if new_count > 0:
                self.new_messages.emit(new_count)
            self.refresh_done.emit()
        except Exception:
            pass

    def run(self) -> None:
        self._last_run = datetime.now()
        while not self._stop.is_set():
            triggered = self._wake.wait(timeout=60.0)
            if self._stop.is_set():
                break
            if triggered:
                self._wake.clear()
                with self._pending_lock:
                    account_id = self._pending_account_id
                    self._pending_account_id = None
                new_count = self.run_one_round(only_account_id=account_id)
                self._emit_round_done(new_count)
                continue

            now = datetime.now()
            if should_trigger_interval(self._last_run, now, self._poll_interval_seconds):
                new_count = self.run_one_round()
                self._emit_round_done(new_count)
