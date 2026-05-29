"""Publish panel — pick folder + time + groups, fire batch publish,
watch progress in real time via PublishQueue signals."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QDateTimeEdit, QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton, QButtonGroup,
)

from publisher.queue import SCHEDULED_MIN_HOURS


class PublishPanel(QWidget):
    def __init__(self, queue, store):
        super().__init__()
        self._queue = queue
        self._store = store
        # Map task_log_id → row index for live updates
        self._row_index: dict[int, int] = {}

        layout = QVBoxLayout(self)

        # Folder picker
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("视频文件夹:"))
        self._folder_edit = QLineEdit()
        self._btn_pick = QPushButton("选择")
        self._btn_pick.clicked.connect(self._on_pick_folder)
        row1.addWidget(self._folder_edit, stretch=1)
        row1.addWidget(self._btn_pick)
        layout.addLayout(row1)

        # Mode + time picker
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("发布模式:"))
        self._radio_immediate = QRadioButton("立即发布")
        self._radio_scheduled = QRadioButton(f"定时发布 (≥{SCHEDULED_MIN_HOURS}h)")
        self._radio_scheduled.setChecked(True)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._radio_immediate)
        self._mode_group.addButton(self._radio_scheduled)
        row2.addWidget(self._radio_immediate)
        row2.addWidget(self._radio_scheduled)
        row2.addSpacing(12)
        row2.addWidget(QLabel("发布时间:"))
        self._time_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(SCHEDULED_MIN_HOURS * 3600 + 60))
        self._time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self._time_edit.setCalendarPopup(True)
        self._time_edit.setMinimumDateTime(QDateTime.currentDateTime().addSecs(SCHEDULED_MIN_HOURS * 3600))
        row2.addWidget(self._time_edit)
        row2.addStretch(1)
        layout.addLayout(row2)
        self._radio_immediate.toggled.connect(lambda checked: self._time_edit.setEnabled(not checked))

        # Group multi-select
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("发布到组:"))
        self._group_list = QListWidget()
        self._group_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._group_list.setMaximumHeight(180)
        self._refresh_groups()
        row3.addWidget(self._group_list, stretch=1)
        col_btns = QVBoxLayout()
        self._btn_select_all = QPushButton("全选")
        self._btn_select_none = QPushButton("全不选")
        self._btn_reload_groups = QPushButton("重新加载组")
        col_btns.addWidget(self._btn_select_all)
        col_btns.addWidget(self._btn_select_none)
        col_btns.addWidget(self._btn_reload_groups)
        col_btns.addStretch(1)
        row3.addLayout(col_btns)
        layout.addLayout(row3)
        self._btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        self._btn_select_none.clicked.connect(lambda: self._set_all_checked(False))
        self._btn_reload_groups.clicked.connect(self._refresh_groups)

        # Publish button
        self._btn_publish = QPushButton("开始发布")
        self._btn_publish.clicked.connect(self._on_publish)
        layout.addWidget(self._btn_publish)

        # Progress table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["组", "视频", "账号", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self._table, stretch=1)

        # Connect queue signals (only if queue is a real PublishQueue)
        if hasattr(queue, "status_changed"):
            queue.status_changed.connect(self._on_status_changed)
        # Start the worker thread
        if hasattr(queue, "start") and not queue.isRunning():
            queue.start()

    # ---- helpers ----
    def _refresh_groups(self):
        self._group_list.clear()
        for g in self._store.list_groups():
            item = QListWidgetItem(f"{g['name']} (#{g['id']})")
            item.setData(Qt.UserRole, g["id"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self._group_list.addItem(item)

    def _set_all_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self._group_list.count()):
            self._group_list.item(i).setCheckState(state)

    def _selected_group_ids(self) -> list[int]:
        out = []
        for i in range(self._group_list.count()):
            item = self._group_list.item(i)
            if item.checkState() == Qt.Checked:
                out.append(int(item.data(Qt.UserRole)))
        return out

    def _on_pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择视频文件夹")
        if folder:
            self._folder_edit.setText(folder)

    # ---- publish action ----
    def _on_publish(self):
        folder = self._folder_edit.text().strip()
        if not folder or not Path(folder).is_dir():
            QMessageBox.warning(self, "无效路径", "请选择有效的视频文件夹")
            return
        videos = sorted([str(p) for p in Path(folder).glob("*.mp4")])
        if not videos:
            QMessageBox.warning(self, "无视频", "该文件夹下没有 MP4 文件")
            return
        groups = self._selected_group_ids()
        if not groups:
            QMessageBox.warning(self, "未选组", "请至少勾选一个组")
            return

        if self._radio_immediate.isChecked():
            scheduled = None
        else:
            scheduled = self._time_edit.dateTime().toPyDateTime()
            min_t = datetime.now() + timedelta(hours=SCHEDULED_MIN_HOURS)
            if scheduled < min_t:
                QMessageBox.warning(
                    self, "时间过早",
                    f"定时发布时间必须 ≥ 当前时间 + {SCHEDULED_MIN_HOURS} 小时（平台规则）"
                )
                return

        # Pair videos[i] → groups[i]; if counts differ, only pair up to the shorter
        pairs = list(zip(videos, groups))
        if len(videos) != len(groups):
            ok = QMessageBox.question(
                self, "数量不一致",
                f"视频数 {len(videos)} ≠ 组数 {len(groups)}，将按顺序配对前 {len(pairs)} 个，是否继续？",
            )
            if ok != QMessageBox.Yes:
                return

        submitted = 0
        for video_path, gid in pairs:
            try:
                task_id = self._queue.submit(video_path, scheduled, gid)
            except Exception as e:
                self._add_progress_row(gid, video_path, None, f"提交失败: {e}")
                continue
            # Add a row per task_log
            for log in self._store.list_task_logs(task_id=task_id):
                self._add_progress_row(gid, video_path, log["account_id"], "等待中", log["id"])
            submitted += 1

        QMessageBox.information(self, "已提交", f"已提交 {submitted} 个任务到队列")

    def _add_progress_row(self, group_id: int, video_path: str, account_id, status: str, log_id: int | None = None):
        row = self._table.rowCount()
        self._table.insertRow(row)
        # Resolve names
        gname = next((g["name"] for g in self._store.list_groups() if g["id"] == group_id), str(group_id))
        aname = ""
        if account_id is not None:
            aname = next((a["display_name"] for a in self._store.list_accounts() if a["id"] == account_id), str(account_id))
        self._table.setItem(row, 0, QTableWidgetItem(gname))
        self._table.setItem(row, 1, QTableWidgetItem(Path(video_path).name))
        self._table.setItem(row, 2, QTableWidgetItem(aname))
        self._table.setItem(row, 3, QTableWidgetItem(status))
        if log_id is not None:
            self._row_index[log_id] = row

    def _on_status_changed(self, log_id: int, account_id: int, status: str):
        row = self._row_index.get(log_id)
        if row is None:
            return
        item = QTableWidgetItem(status)
        if status == "failed":
            item.setForeground(Qt.red)
        elif status == "submitted":
            item.setForeground(Qt.darkGreen)
        self._table.setItem(row, 3, item)
