"""Douyin work cleanup panel."""
from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from publisher.douyin_cleanup import CleanupResult, DouyinCleanupRunner, DouyinWorkCleaner


class _CleanupWorker(QThread):
    result = pyqtSignal(object)
    progress = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, accounts: list[dict]):
        super().__init__()
        self._accounts = accounts
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def _stop_requested(self) -> bool:
        return self._stop

    def run(self) -> None:
        try:
            runner = DouyinCleanupRunner(self._accounts, stop_requested=self._stop_requested)
            for item in runner.run():
                self.result.emit(item)
                if isinstance(item, CleanupResult):
                    self.progress.emit(f"正在处理账号：{item.account_name}")
                if self._stop:
                    break
            self.done.emit()
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class _RetryWorker(QThread):
    result = pyqtSignal(object)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, jobs: list[tuple[dict, CleanupResult]]):
        super().__init__()
        self._jobs = jobs
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            cleaner = DouyinWorkCleaner()
            for account, failed in self._jobs:
                if self._stop:
                    break
                results = cleaner.clean_account(
                    account,
                    stop_requested=lambda: self._stop,
                    target_title=failed.title,
                    target_publish_time=failed.publish_time,
                )
                for item in results:
                    self.result.emit(item)
            self.done.emit()
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")


class CleanupPanel(QWidget):
    def __init__(self, store):
        super().__init__()
        self._store = store
        self._worker: _CleanupWorker | None = None
        self._retry_worker: _RetryWorker | None = None
        self._records: list[CleanupResult] = []
        self._scanned = 0
        self._deleted = 0
        self._skipped = 0
        self._failed = 0

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self._btn_start = QPushButton("清理所有抖音账号低效作品")
        self._btn_stop = QPushButton("停止")
        self._btn_retry_failed = QPushButton("重试选中失败")
        self._btn_delete_selected = QPushButton("删除选中记录")
        self._btn_clear = QPushButton("清空记录")
        self._btn_stop.setEnabled(False)
        self._status = QLabel("未开始")
        top.addWidget(self._btn_start)
        top.addWidget(self._btn_stop)
        top.addWidget(self._btn_retry_failed)
        top.addWidget(self._btn_delete_selected)
        top.addWidget(self._btn_clear)
        top.addWidget(self._status, stretch=1)
        layout.addLayout(top)

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["账号", "标题", "发布时间", "播放", "点赞", "原因", "结果", "截图/错误"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self._table, stretch=1)

        self._btn_start.clicked.connect(self._start)
        self._btn_stop.clicked.connect(self._stop_run)
        self._btn_retry_failed.clicked.connect(self._retry_selected_failed)
        self._btn_delete_selected.clicked.connect(self._delete_selected_records)
        self._btn_clear.clicked.connect(self._clear_records)

    def _start(self) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "正在清理", "当前已经有清理任务在运行")
            return
        if self._retry_worker and self._retry_worker.isRunning():
            QMessageBox.information(self, "正在重试", "当前已经有重试任务在运行")
            return

        accounts = [
            account
            for account in self._store.list_accounts()
            if account.get("platform") == "douyin" and int(account.get("is_active") or 0) == 1
        ]
        if not accounts:
            QMessageBox.information(self, "无账号", "当前没有启用的抖音账号")
            return

        self._reset()
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._status.setText(f"准备清理 {len(accounts)} 个抖音账号")

        self._worker = _CleanupWorker(accounts)
        self._worker.result.connect(self._append_result)
        self._worker.progress.connect(self._set_progress)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop_run(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._btn_stop.setEnabled(False)
            self._status.setText("正在停止，等待当前浏览器操作结束")
        if self._retry_worker and self._retry_worker.isRunning():
            self._retry_worker.request_stop()
            self._btn_stop.setEnabled(False)
            self._status.setText("正在停止，等待当前浏览器操作结束")

    def _reset(self) -> None:
        self._table.setRowCount(0)
        self._records = []
        self._scanned = 0
        self._deleted = 0
        self._skipped = 0
        self._failed = 0

    def _append_result(self, result: object) -> None:
        if not isinstance(result, CleanupResult):
            return
        self._records.append(result)
        row = self._table.rowCount()
        self._table.insertRow(row)
        values = [
            result.account_name,
            result.title,
            result.publish_time,
            result.plays,
            result.likes,
            result.reason,
            result.status,
            result.detail,
        ]
        for column, value in enumerate(values):
            self._table.setItem(row, column, QTableWidgetItem(str(value or "")))

        self._scanned += 1
        if result.status == "已删除":
            self._deleted += 1
        elif result.status == "失败":
            self._failed += 1
        else:
            self._skipped += 1
        self._update_summary()

    def _delete_selected_records(self) -> None:
        rows = sorted({i.row() for i in self._table.selectedIndexes()}, reverse=True)
        if not rows:
            QMessageBox.information(self, "未选中", "请先选中要删除的清理记录")
            return
        for row in rows:
            if 0 <= row < len(self._records):
                self._records.pop(row)
                self._table.removeRow(row)
        self._recount_records()
        self._update_summary()

    def _clear_records(self) -> None:
        if not self._records:
            return
        self._records = []
        self._table.setRowCount(0)
        self._recount_records()
        self._update_summary()

    def _retry_selected_failed(self) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "正在清理", "请等待当前清理任务结束后再重试")
            return
        if self._retry_worker and self._retry_worker.isRunning():
            QMessageBox.information(self, "正在重试", "当前已经有重试任务在运行")
            return

        rows = sorted({i.row() for i in self._table.selectedIndexes()})
        failed = [
            self._records[row]
            for row in rows
            if 0 <= row < len(self._records) and self._records[row].status == "失败"
        ]
        if not failed:
            QMessageBox.information(self, "无失败记录", "请选择结果为“失败”的记录")
            return

        accounts = {int(a["id"]): a for a in self._store.list_accounts()}
        jobs: list[tuple[dict, CleanupResult]] = []
        missing = 0
        for record in failed:
            account = accounts.get(record.account_id)
            if account:
                jobs.append((account, record))
            else:
                missing += 1

        if not jobs:
            QMessageBox.warning(self, "无法重试", "选中的失败记录找不到对应账号")
            return

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._status.setText(f"准备重试 {len(jobs)} 条失败记录")
        if missing:
            QMessageBox.information(self, "部分跳过", f"{missing} 条失败记录找不到对应账号，已跳过")

        self._retry_worker = _RetryWorker(jobs)
        self._retry_worker.result.connect(self._append_result)
        self._retry_worker.done.connect(self._on_done)
        self._retry_worker.error.connect(self._on_error)
        self._retry_worker.start()

    def _recount_records(self) -> None:
        self._scanned = len(self._records)
        self._deleted = sum(1 for r in self._records if r.status == "已删除")
        self._failed = sum(1 for r in self._records if r.status == "失败")
        self._skipped = self._scanned - self._deleted - self._failed

    def _set_progress(self, text: str) -> None:
        self._status.setText(text)

    def _update_summary(self) -> None:
        self._status.setText(
            f"已扫描 {self._scanned} 条；删除 {self._deleted} 条；"
            f"跳过 {self._skipped} 条；失败 {self._failed} 条"
        )

    def _on_done(self) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._update_summary()

    def _on_error(self, message: str) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        QMessageBox.critical(self, "清理失败", message)
