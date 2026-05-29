"""Read-only stranger-message inbox panel."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMenu,
    QSystemTrayIcon,
    QStyle,
    QMessageBox,
)

from mediapush_ui.browser_launcher import IndependentChromiumLauncher
from mediapush_ui.reply_dialog import ReplyDialog
from publisher.douyin_message import URL_CHAT
from publisher.message_reader import Message
from publisher.message_scheduler import MessageScheduler
from publisher.message_store import MessageStore


SCHEDULE_LABEL = "每 1 小时"


class MessagePanel(QWidget):
    def __init__(
        self,
        store,
        msg_store: MessageStore,
        scheduler: MessageScheduler,
        readers: dict,
        parent=None,
    ):
        super().__init__(parent)
        self._store = store
        self._msg_store = msg_store
        self._scheduler = scheduler
        self._readers = readers
        self._row_msgs: list[Message] = []
        self._launcher = IndependentChromiumLauncher()

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self._tray.setVisible(True)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self._btn_refresh_all = QPushButton("刷新全部")
        self._btn_refresh_all.clicked.connect(self._refresh_all)
        top.addWidget(self._btn_refresh_all)

        top.addStretch(1)
        top.addWidget(QLabel(f"自动轮询: {SCHEDULE_LABEL}"))
        layout.addLayout(top)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(["分组", "账号", "用户", "消息预览", "时间", "抓取于", "会话ID"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.cellDoubleClicked.connect(self._open_chat_backend)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 110)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self._table.setColumnWidth(1, 130)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self._table.setColumnWidth(2, 140)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self._table.setColumnWidth(4, 80)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self._table.setColumnWidth(5, 110)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self._table.setColumnHidden(6, True)
        layout.addWidget(self._table, stretch=1)

        self._status = QLabel("当前 0 条消息")
        layout.addWidget(self._status)

        self._scheduler.refresh_done.connect(self._refresh_table)
        self._scheduler.new_messages.connect(self._notify)
        self._scheduler.account_status.connect(self._on_account_status)

        self._refresh_table()
        QTimer.singleShot(1000, self._refresh_all)

    def _refresh_all(self) -> None:
        self._set_refreshing(True, "正在刷新全部账号...")
        self._scheduler.trigger_now(None)

    def _set_refreshing(self, refreshing: bool, status: str | None = None) -> None:
        self._btn_refresh_all.setEnabled(not refreshing)
        if status:
            self._status.setText(status)

    def _refresh_table(self) -> None:
        self._row_msgs = self._msg_store.list_all()
        account_groups = self._account_group_names()
        self._table.setRowCount(0)
        for msg in self._row_msgs:
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = [
                account_groups.get(msg.account_id, ""),
                msg.account_name,
                msg.user_name,
                msg.preview,
                msg.timestamp_str,
                msg.fetched_at.strftime("%H:%M:%S"),
                msg.conversation_id,
            ]
            for col, value in enumerate(values):
                self._table.setItem(row, col, QTableWidgetItem(value))
        self._set_refreshing(False)
        self._status.setText(f"当前 {len(self._row_msgs)} 条消息")

    def _account_group_names(self) -> dict[int, str]:
        groups = {group["id"]: group["name"] for group in self._store.list_groups()}
        out: dict[int, str] = {}
        for account in self._store.list_accounts():
            out[account["id"]] = groups.get(account["group_id"], "")
        return out

    def _on_context_menu(self, pos: QPoint) -> None:
        row = self._table.indexAt(pos).row()
        if row < 0 or row >= len(self._row_msgs):
            return
        menu = QMenu(self)
        open_backend = menu.addAction("打开私信后台")
        reply = menu.addAction("回复")
        mark_seen = menu.addAction("标记已处理")
        action = menu.exec_(self._table.viewport().mapToGlobal(pos))
        if action == open_backend:
            self._open_chat_backend(row, 0)
        elif action == reply:
            self._open_reply_dialog(row, 0)
        elif action == mark_seen:
            msg = self._row_msgs[row]
            self._msg_store.mark_seen(msg.account_id, msg.conversation_id)
            self._refresh_table()

    def _open_chat_backend(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._row_msgs):
            return
        msg = self._row_msgs[row]
        account = next((item for item in self._store.list_accounts() if item["id"] == msg.account_id), None)
        if account is None:
            QMessageBox.warning(self, "账号不存在", "找不到这条消息对应的账号")
            return
        if account.get("platform") != "douyin":
            QMessageBox.warning(self, "暂不支持", f"当前仅支持打开抖音私信后台，账号平台为 {account.get('platform')}")
            return
        profile_path = account.get("profile_path") or ""
        if not profile_path:
            QMessageBox.warning(self, "无法打开", "这个账号没有本地浏览器 Profile 路径")
            return
        self._launcher.open_creator_backend(profile_path, URL_CHAT)

    def _open_reply_dialog(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._row_msgs):
            return
        msg = self._row_msgs[row]
        account = next((item for item in self._store.list_accounts() if item["id"] == msg.account_id), None)
        if account is None:
            QMessageBox.warning(self, "账号不存在", "找不到这条消息对应的账号")
            return
        reader = self._readers.get(account["platform"])
        if reader is None:
            QMessageBox.warning(self, "平台不可用", f"未配置 {account['platform']} 的私信读取器")
            return

        self._msg_store.mark_busy(msg.account_id)
        try:
            dialog = ReplyDialog(msg, account["profile_path"], reader, parent=self)
            dialog.sent.connect(self._on_reply_sent)
            dialog.exec_()
        finally:
            self._msg_store.mark_idle(msg.account_id)
            self._refresh_table()

    def _on_reply_sent(self, account_id: int, conversation_id: str) -> None:
        self._msg_store.mark_seen(account_id, conversation_id)

    def _notify(self, count: int) -> None:
        self._tray.showMessage(
            "MediaPush - 新陌生人私信",
            f"本轮更新 {count} 条消息",
            QSystemTrayIcon.Information,
            5000,
        )

    def _on_account_status(self, account_id: int, status: str) -> None:
        account = next((item for item in self._store.list_accounts() if item["id"] == account_id), None)
        name = account["display_name"] if account else str(account_id)
        if status == "fetching":
            self._status.setText(f"账号 [{name}] 抓取中...")
        elif status == "error":
            self._status.setText(f"账号 [{name}] 抓取失败")
