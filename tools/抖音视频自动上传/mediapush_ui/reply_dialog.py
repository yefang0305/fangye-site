"""Dialog for manually replying to one stranger message."""
from __future__ import annotations

from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
)

from publisher.message_reader import ChatMessage, Message, MessageReader


CHAT_REFRESH_MS = 20_000


class _SendWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, reader: MessageReader, profile_path: str, conversation_id: str, text: str):
        super().__init__()
        self._reader = reader
        self._profile_path = profile_path
        self._conversation_id = conversation_id
        self._text = text

    def run(self) -> None:
        try:
            ok, err = self._reader.reply(self._profile_path, self._conversation_id, self._text)
            self.done.emit(ok, err)
        except Exception as exc:
            self.done.emit(False, f"{type(exc).__name__}: {exc}")


class _HistoryWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, reader: MessageReader, profile_path: str, conversation_id: str):
        super().__init__()
        self._reader = reader
        self._profile_path = profile_path
        self._conversation_id = conversation_id

    def run(self) -> None:
        try:
            self.done.emit(self._reader.fetch_conversation_messages(self._profile_path, self._conversation_id))
        except Exception:
            self.done.emit([])


class ReplyDialog(QDialog):
    sent = pyqtSignal(int, str)

    def __init__(self, message: Message, profile_path: str, reader: MessageReader, parent=None):
        super().__init__(parent)
        self._message = message
        self._profile_path = profile_path
        self._reader = reader
        self._worker: _SendWorker | None = None
        self._history_worker: _HistoryWorker | None = None
        self._refreshing_history = False

        self.setWindowTitle(f"回复 [{message.user_name}]")
        self.resize(620, 520)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"账号: {message.account_name}"))
        layout.addWidget(QLabel(f"对方: {message.user_name}"))

        self._history = QListWidget()
        layout.addWidget(self._history, stretch=2)

        layout.addWidget(QLabel("回复内容:"))
        self._input = QPlainTextEdit()
        layout.addWidget(self._input, stretch=1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_send = QPushButton("发送")
        self._btn_send.clicked.connect(self._send)
        buttons.addWidget(self._btn_cancel)
        buttons.addWidget(self._btn_send)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setInterval(CHAT_REFRESH_MS)
        self._timer.timeout.connect(self._refresh_history)
        self._timer.start()
        self._refresh_history()

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)

    def _refresh_history(self) -> None:
        if self._refreshing_history:
            return
        self._refreshing_history = True
        self._history_worker = _HistoryWorker(self._reader, self._profile_path, self._message.conversation_id)
        self._history_worker.done.connect(self._on_history)
        self._history_worker.start()

    def _on_history(self, messages: list[ChatMessage]) -> None:
        self._refreshing_history = False
        self._history.clear()
        if not messages:
            item = QListWidgetItem(f"对方: {self._message.preview}")
            self._history.addItem(item)
            return
        for message in messages:
            prefix = "我" if message.sender == "me" else "对方"
            self._history.addItem(QListWidgetItem(f"{prefix}: {message.text}"))
        self._history.scrollToBottom()

    def _send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "空内容", "请输入回复内容")
            return

        self._input.setEnabled(False)
        self._btn_cancel.setEnabled(False)
        self._btn_send.setEnabled(False)
        self._btn_send.setText("发送中...")

        self._worker = _SendWorker(
            self._reader,
            self._profile_path,
            self._message.conversation_id,
            text,
        )
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok: bool, err: str) -> None:
        self._input.setEnabled(True)
        self._btn_cancel.setEnabled(True)
        self._btn_send.setEnabled(True)
        self._btn_send.setText("发送")
        if ok:
            self.sent.emit(self._message.account_id, self._message.conversation_id)
            self._input.clear()
            self._refresh_history()
            return
        QMessageBox.critical(self, "发送失败", err or "未知错误")
