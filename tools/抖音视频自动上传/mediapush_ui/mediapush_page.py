"""Self-contained MediaPush page for embedding into VideoCut's sidebar.

Exposes a single QWidget (`MediaPushPage`) that hosts the three existing
panels (account / publish / history) inside a QTabWidget. All MediaPush
backend objects (Store, PublishQueue, InboxWatcher, AccountManager) are
instantiated here so the host application doesn't need to know about them.

VideoCut's main_window does:

    from ui.mediapush_page import MediaPushPage   # after sys.path setup
    self.mediapush_page = MediaPushPage()
    self.stacked.addWidget(self.mediapush_page)

The page reads the same `MEDIAPUSH_*` env vars as MediaPush's standalone
main.py — but falls back to MediaPush-project-relative defaults if they're
not set, so it works even from a VideoCut process that doesn't have a
.env file pointing at MediaPush paths.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from db.store import Store
from account.manager import AccountManager
from publisher.queue import PublishQueue
from publisher.inbox_watcher import InboxWatcher
from publisher.douyin import DouyinPublisher
from publisher.xiaohongshu import XiaohongshuPublisher
from publisher.kuaishou import KuaishouPublisher
from publisher.douyin_message import DouyinMessageReader
from publisher.message_scheduler import MessageScheduler
from publisher.message_store import MessageStore

from mediapush_ui.account_panel import AccountPanel
from mediapush_ui.publish_panel import PublishPanel
from mediapush_ui.history_panel import HistoryPanel
from mediapush_ui.message_panel import MessagePanel
from mediapush_ui.cleanup_panel import CleanupPanel


# MediaPush project root (this file lives in <root>/ui/)
_MP_ROOT = Path(__file__).resolve().parent.parent


def _resolve_paths() -> tuple[str, str, str, str, float]:
    """Return (db_path, profiles_path, inbox_path, processed_path, poll_sec)."""
    db_path = os.environ.get("MEDIAPUSH_DB_PATH", str(_MP_ROOT / "data" / "mediapush.db"))
    profiles = os.environ.get("MEDIAPUSH_PROFILES_PATH", str(_MP_ROOT / "profiles"))
    inbox = os.environ.get("MEDIAPUSH_INBOX_PATH", str(_MP_ROOT / "inbox"))
    processed = os.environ.get(
        "MEDIAPUSH_INBOX_PROCESSED_PATH", str(Path(inbox) / "processed")
    )
    poll = float(os.environ.get("MEDIAPUSH_INBOX_POLL_SECONDS", "5"))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(profiles).mkdir(parents=True, exist_ok=True)
    Path(inbox).mkdir(parents=True, exist_ok=True)
    Path(processed).mkdir(parents=True, exist_ok=True)
    return db_path, profiles, inbox, processed, poll


class MediaPushPage(QWidget):
    """The full MediaPush UI as one embeddable widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        db_path, profiles, inbox, processed, poll = _resolve_paths()

        self.store = Store(db_path)
        if os.environ.get("MEDIAPUSH_AUTO_PURGE_HISTORY", "1") != "0":
            self.store.purge_submitted_history_before(date.today().isoformat())
        self.publishers = {
            "douyin": DouyinPublisher(),
            "xiaohongshu": XiaohongshuPublisher(),
            "kuaishou": KuaishouPublisher(),
        }
        self.account_mgr = AccountManager(self.store, profiles, publishers=self.publishers)
        self.queue = PublishQueue(self.store, publishers=self.publishers)
        self.queue.start()
        self.watcher = InboxWatcher(self.store, self.queue, inbox, processed, poll_sec=poll)
        self.watcher.start()
        self.msg_store = MessageStore(Path(db_path).parent / "message_seen.json")
        self.message_readers = {"douyin": DouyinMessageReader()}
        self.message_scheduler = MessageScheduler(self.store, self.msg_store, self.message_readers)
        self.message_scheduler.start()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget(self)
        self.tabs.addTab(AccountPanel(self.account_mgr), "账号管理")
        self.tabs.addTab(PublishPanel(self.queue, self.store), "发布任务")
        self.tabs.addTab(HistoryPanel(self.store, self.queue), "发布记录")
        self.tabs.addTab(CleanupPanel(self.store), "作品清理")
        self.tabs.addTab(
            MessagePanel(self.store, self.msg_store, self.message_scheduler, self.message_readers),
            "私信管理",
        )
        layout.addWidget(self.tabs)

    def cleanup(self) -> None:
        """Stop background threads. Optional — VideoCut's closeEvent calls
        os._exit(0) which kills all threads anyway, but exposing this lets
        future callers do graceful shutdown."""
        try:
            self.message_scheduler.stop()
            self.message_scheduler.wait(3000)
        except Exception:
            pass
        try:
            self.watcher.stop()
            self.watcher.wait(2000)
        except Exception:
            pass
        try:
            self.queue.stop()
            self.queue.wait(2000)
        except Exception:
            pass
        try:
            self.store.close()
        except Exception:
            pass
