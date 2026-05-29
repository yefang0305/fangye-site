"""History panel — flat table of all task_logs with the related task/account info.

Supports retrying failed/stranded logs, explicitly re-trying verified-missing
submitted logs, deleting selected history rows, and double-clicking a row to
open the related Douyin creator content list in a headed browser.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from mediapush_ui.browser_launcher import IndependentChromiumLauncher


DOUYIN_CONTENT_MANAGE_URL = "https://creator.douyin.com/creator-micro/content/manage"


class HistoryPanel(QWidget):
    def __init__(self, store, queue=None):
        super().__init__()
        self._store = store
        self._queue = queue
        self._launcher = IndependentChromiumLauncher()
        # row index → task_log id, so retry actions know what to re-enqueue
        self._row_log_ids: list[int] = []

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self._btn_refresh = QPushButton("刷新")
        self._btn_refresh.clicked.connect(self._refresh)
        self._btn_retry_selected = QPushButton("重试选中")
        self._btn_retry_selected.clicked.connect(self._retry_selected)
        self._btn_retry_all_failed = QPushButton("重试全部失败")
        self._btn_retry_all_failed.clicked.connect(self._retry_all_failed)
        self._btn_delete_selected = QPushButton("删除选中记录")
        self._btn_delete_selected.clicked.connect(self._delete_selected)
        for b in (
            self._btn_refresh,
            self._btn_retry_selected,
            self._btn_retry_all_failed,
            self._btn_delete_selected,
        ):
            top.addWidget(b)
        top.addStretch(1)
        layout.addLayout(top)

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["提交时间", "定时发布时间", "视频", "组", "账号", "状态", "重试", "错误信息"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._open_creator_manage)
        layout.addWidget(self._table, stretch=1)

        if self._queue is not None:
            # Live updates from the worker thread → refresh rows automatically.
            self._queue.status_changed.connect(self._on_status_changed)

        self._refresh()

    # ---- data load ----
    def _refresh(self):
        accounts = {a["id"]: a for a in self._store.list_accounts()}
        groups = {g["id"]: g for g in self._store.list_groups()}
        tasks = {t["id"]: t for t in self._store.list_tasks()}
        logs = self._store.list_task_logs()

        self._row_log_ids = []
        self._table.setRowCount(0)
        for log in logs:
            task = tasks.get(log["task_id"], {})
            acc = accounts.get(log["account_id"], {})
            gid = task.get("group_id")
            gname = groups.get(gid, {}).get("name", str(gid))
            video = Path(task.get("video_path", "")).name
            sched = task.get("scheduled_time") or "立即"
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._row_log_ids.append(log["id"])
            self._table.setItem(row, 0, QTableWidgetItem(log.get("submitted_at") or ""))
            self._table.setItem(row, 1, QTableWidgetItem(sched))
            self._table.setItem(row, 2, QTableWidgetItem(video))
            self._table.setItem(row, 3, QTableWidgetItem(gname))
            self._table.setItem(row, 4, QTableWidgetItem(acc.get("display_name", "")))
            self._table.setItem(row, 5, QTableWidgetItem(log.get("status", "")))
            # Attempt count is informational only — first attempt is headless,
            # any attempt > 1 (auto-retry once + manual retries) runs headed.
            attempts = log.get("attempt_count", 1)
            self._table.setItem(row, 6, QTableWidgetItem(f"已尝试 {attempts} 次"))
            self._table.setItem(row, 7, QTableWidgetItem(log.get("error_msg") or ""))

    # ---- helpers ----
    def _snapshot_by_id(self) -> tuple[dict[int, dict], dict[int, dict]]:
        tasks = {t["id"]: t for t in self._store.list_tasks()}
        logs = {l["id"]: l for l in self._store.list_task_logs()}
        return tasks, logs

    def _log_for_row(self, row: int) -> dict | None:
        if row < 0 or row >= len(self._row_log_ids):
            return None
        log_id = self._row_log_ids[row]
        return next((l for l in self._store.list_task_logs() if l["id"] == log_id), None)

    @staticmethod
    def _parse_scheduled_time(raw: str | None) -> datetime | None:
        if not raw:
            return None
        return datetime.fromisoformat(raw)

    # ---- retry actions ----
    def _retry_selected(self):
        if self._queue is None:
            QMessageBox.warning(self, "不可用", "队列未注入，无法重试")
            return
        rows = sorted({i.row() for i in self._table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "未选中", "请先选中要重试的行")
            return
        tasks, logs = self._snapshot_by_id()
        ok, skipped = 0, 0
        blocked: list[str] = []
        for r in rows:
            if r < 0 or r >= len(self._row_log_ids):
                continue
            log_id = self._row_log_ids[r]
            log = logs.get(log_id)
            if not log:
                skipped += 1
                continue
            status = log.get("status", "")
            if status in {"failed", "pending", "uploading"}:
                if self._queue.retry(log_id, allow_incomplete=True):
                    ok += 1
                else:
                    skipped += 1
                continue
            if status == "submitted":
                task = tasks.get(log.get("task_id"), {})
                try:
                    scheduled = self._parse_scheduled_time(task.get("scheduled_time"))
                    self._queue.validate_time(scheduled)
                except Exception as e:
                    video = Path(task.get("video_path", "")).name or f"记录#{log_id}"
                    blocked.append(f"{video}: {e}")
                    skipped += 1
                    continue
                if self._queue.retry(log_id, allow_submitted=True):
                    ok += 1
                else:
                    skipped += 1
                continue
            skipped += 1
        detail = ""
        if blocked:
            detail = "\n\n以下记录定时时间已过或不满足平台提前量，未重试：\n" + "\n".join(blocked[:5])
            if len(blocked) > 5:
                detail += f"\n...等 {len(blocked)} 条"
        self._refresh()
        QMessageBox.information(
            self, "已重试",
            f"已重新入队 {ok} 个；跳过 {skipped} 个。"
            "\n失败、pending、uploading 记录可直接重试；submitted 记录会在定时时间仍有效时重试。"
            f"{detail}",
        )

    # ---- creator backend ----
    def _open_creator_manage(self, row: int, _column: int):
        log = self._log_for_row(row)
        if not log:
            return
        acc = next((a for a in self._store.list_accounts() if a["id"] == log["account_id"]), None)
        if not acc:
            QMessageBox.warning(self, "无法打开", "找不到这条记录对应的账号")
            return
        if acc.get("platform") != "douyin":
            QMessageBox.warning(self, "暂不支持", f"当前仅支持打开抖音作品列表，账号平台为 {acc.get('platform')}")
            return
        profile_path = acc.get("profile_path") or ""
        if not profile_path:
            QMessageBox.warning(self, "无法打开", "这个账号没有本地浏览器 Profile 路径")
            return
        self._launcher.open_creator_backend(profile_path, DOUYIN_CONTENT_MANAGE_URL)

    def _retry_all_failed(self):
        if self._queue is None:
            QMessageBox.warning(self, "不可用", "队列未注入，无法重试")
            return
        failed_ids = [l["id"] for l in self._store.list_task_logs() if l["status"] == "failed"]
        if not failed_ids:
            QMessageBox.information(self, "无失败任务", "当前没有失败状态的任务")
            return
        confirm = QMessageBox.question(
            self, "确认重试", f"将重新入队 {len(failed_ids)} 个失败任务，是否继续？",
        )
        if confirm != QMessageBox.Yes:
            return
        ok = sum(1 for lid in failed_ids if self._queue.retry(lid))
        self._refresh()
        QMessageBox.information(self, "已重试", f"已重新入队 {ok} 个任务")

    # ---- delete actions ----
    def _delete_selected(self):
        rows = sorted({i.row() for i in self._table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "未选中", "请先选中要删除的发布记录")
            return

        log_ids = [
            self._row_log_ids[r]
            for r in rows
            if 0 <= r < len(self._row_log_ids)
        ]
        if not log_ids:
            QMessageBox.information(self, "未选中", "没有可删除的发布记录")
            return

        confirm = QMessageBox.question(
            self,
            "确认删除",
            f"将删除选中的 {len(log_ids)} 条发布记录。\n\n"
            "只删除记录，不删除视频文件。是否继续？",
        )
        if confirm != QMessageBox.Yes:
            return

        result = self._store.delete_task_logs(log_ids)
        self._refresh()
        QMessageBox.information(
            self,
            "已删除",
            f"已删除 {result['task_logs']} 条发布记录。",
        )

    # ---- live updates ----
    def _on_status_changed(self, log_id: int, _account_id: int, _status: str):
        # Cheap and correct: just reload. The table is small (one row per
        # task×account) and refresh runs on the UI thread.
        self._refresh()
