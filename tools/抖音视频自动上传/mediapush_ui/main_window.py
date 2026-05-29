"""Main window — tabs hosting the panels.

The constructor takes already-built dependencies (account_mgr, queue, store)
so the window is a pure composition root. Panels are imported lazily later
to keep this file as a thin shell.
"""
from __future__ import annotations

from PyQt5.QtWidgets import QMainWindow, QTabWidget, QWidget, QLabel, QVBoxLayout


class _Placeholder(QWidget):
    def __init__(self, label: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))


class MainWindow(QMainWindow):
    def __init__(
        self,
        account_mgr=None,
        queue=None,
        store=None,
        msg_store=None,
        scheduler=None,
        message_readers=None,
    ):
        super().__init__()
        self.setWindowTitle("MediaPush")
        self.resize(1000, 700)

        self._account_mgr = account_mgr
        self._queue = queue
        self._store = store
        self._msg_store = msg_store
        self._scheduler = scheduler
        self._message_readers = message_readers or {}

        self._tabs = QTabWidget(self)
        self.setCentralWidget(self._tabs)

        self._build_tabs()

    def _build_tabs(self) -> None:
        # Lazy import so missing panels don't crash when running smoke tests.
        try:
            from mediapush_ui.account_panel import AccountPanel
            account_tab = AccountPanel(self._account_mgr) if self._account_mgr else _Placeholder("账号管理（未注入依赖）")
        except ImportError:
            account_tab = _Placeholder("账号管理（待实现）")

        try:
            from mediapush_ui.publish_panel import PublishPanel
            publish_tab = (
                PublishPanel(self._queue, self._store)
                if self._queue and self._store
                else _Placeholder("发布任务（未注入依赖）")
            )
        except ImportError:
            publish_tab = _Placeholder("发布任务（待实现）")

        try:
            from mediapush_ui.history_panel import HistoryPanel
            history_tab = HistoryPanel(self._store, self._queue) if self._store else _Placeholder("发布记录（未注入依赖）")
        except ImportError:
            history_tab = _Placeholder("发布记录（待实现）")

        try:
            from mediapush_ui.cleanup_panel import CleanupPanel
            cleanup_tab = CleanupPanel(self._store) if self._store else _Placeholder("作品清理（未注入依赖）")
        except ImportError:
            cleanup_tab = _Placeholder("作品清理（待实现）")

        try:
            from mediapush_ui.message_panel import MessagePanel
            message_tab = (
                MessagePanel(self._store, self._msg_store, self._scheduler, self._message_readers)
                if self._store and self._msg_store and self._scheduler
                else _Placeholder("私信管理（未注入依赖）")
            )
        except ImportError:
            message_tab = _Placeholder("私信管理（待实现）")

        self._tabs.addTab(account_tab, "账号管理")
        self._tabs.addTab(publish_tab, "发布任务")
        self._tabs.addTab(history_tab, "发布记录")
        self._tabs.addTab(cleanup_tab, "作品清理")
        self._tabs.addTab(message_tab, "私信管理")
