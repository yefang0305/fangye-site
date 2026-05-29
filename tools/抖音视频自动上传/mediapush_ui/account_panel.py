"""Account management panel — group/account tree with full CRUD,
multi-platform QR add, WEMedia scan, double-click to open creator backend."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QThread, QPoint, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QMessageBox, QMenu, QAction,
)

from mediapush_ui.browser_launcher import IndependentChromiumLauncher


_STATUS_ICON = {True: "● 已登录", False: "○ 已失效"}


class _LoginRefreshThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, account_mgr):
        super().__init__()
        self._mgr = account_mgr

    def run(self):
        try:
            self.done.emit(self._mgr.refresh_all_login_status())
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class _QrAddThread(QThread):
    done = pyqtSignal(int, str)  # account_id, detected_name
    error = pyqtSignal(str)

    def __init__(self, account_mgr, group_id: int, platform: str):
        super().__init__()
        self._mgr = account_mgr
        self._gid = group_id
        self._platform = platform

    def run(self):
        try:
            aid, name = self._mgr.add_via_qr(self._gid, platform=self._platform)
            self.done.emit(aid, name)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class AccountPanel(QWidget):
    def __init__(self, account_mgr):
        super().__init__()
        self._mgr = account_mgr
        self._store = account_mgr._store
        self._publishers = account_mgr._publishers
        self._launcher = IndependentChromiumLauncher()

        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self._btn_new_group = QPushButton("新建组")
        self._btn_qr = QPushButton("添加账号(扫码)")
        self._btn_refresh = QPushButton("刷新登录状态")
        for b in (self._btn_new_group, self._btn_qr, self._btn_refresh):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["名称", "平台", "状态"])
        self._tree.setColumnWidth(0, 360)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree, stretch=1)

        self._btn_new_group.clicked.connect(self._on_new_group)
        self._btn_qr.clicked.connect(self._on_add_qr)
        self._btn_refresh.clicked.connect(self._on_refresh)

        self._refresh_tree()

    # ---- helpers ----
    def _refresh_tree(self):
        self._tree.clear()
        for g in self._store.list_groups():
            g_item = QTreeWidgetItem([f"{g['name']} (#{g['id']})", "", ""])
            g_item.setData(0, Qt.UserRole, ("group", g["id"]))
            for a in self._store.list_accounts(group_id=g["id"]):
                pub = self._publishers.get(a["platform"])
                pname = pub.display_name if pub else a["platform"]
                child = QTreeWidgetItem([a["display_name"], pname, _STATUS_ICON[a["is_active"] == 1]])
                child.setData(0, Qt.UserRole, ("account", a["id"]))
                g_item.addChild(child)
            self._tree.addTopLevelItem(g_item)
        self._tree.expandAll()

    def _pick_group_id(self) -> int | None:
        groups = self._store.list_groups()
        if not groups:
            QMessageBox.warning(self, "无组", "请先新建一个组")
            return None
        names = [f"{g['name']} (#{g['id']})" for g in groups]
        choice, ok = QInputDialog.getItem(self, "选择组", "选择目标组:", names, 0, False)
        return groups[names.index(choice)]["id"] if ok else None

    def _pick_platform(self) -> str | None:
        if not self._publishers:
            QMessageBox.warning(self, "无平台", "未注册任何 Publisher")
            return None
        items = [(p.display_name, key) for key, p in self._publishers.items()]
        labels = [name for name, _ in items]
        choice, ok = QInputDialog.getItem(self, "选择平台", "选择登录平台:", labels, 0, False)
        return items[labels.index(choice)][1] if ok else None

    # ---- top-bar handlers ----
    def _on_new_group(self):
        name, ok = QInputDialog.getText(self, "新建组", "组名:")
        if ok and name.strip():
            self._store.create_group(name.strip())
            self._refresh_tree()

    def _on_add_qr(self):
        platform = self._pick_platform()
        if platform is None:
            return
        gid = self._pick_group_id()
        if gid is None:
            return
        self._btn_qr.setEnabled(False)
        self._qr_thread = _QrAddThread(self._mgr, gid, platform)
        self._qr_thread.done.connect(self._on_qr_done)
        self._qr_thread.error.connect(self._on_qr_error)
        self._qr_thread.start()

    def _on_qr_done(self, _aid: int, name: str):
        self._btn_qr.setEnabled(True)
        self._refresh_tree()
        QMessageBox.information(self, "成功", f"账号添加成功，识别到名称：{name}")

    def _on_qr_error(self, msg: str):
        self._btn_qr.setEnabled(True)
        QMessageBox.critical(self, "扫码失败", msg)

    def _on_refresh(self):
        self._btn_refresh.setEnabled(False)
        self._refresh_thread = _LoginRefreshThread(self._mgr)
        self._refresh_thread.done.connect(self._on_refresh_done)
        self._refresh_thread.error.connect(self._on_refresh_error)
        self._refresh_thread.start()

    def _on_refresh_done(self, _result: dict):
        self._btn_refresh.setEnabled(True)
        self._refresh_tree()

    def _on_refresh_error(self, msg: str):
        self._btn_refresh.setEnabled(True)
        QMessageBox.critical(self, "刷新失败", msg)

    # ---- right-click menu ----
    def _on_context_menu(self, pos: QPoint):
        item = self._tree.itemAt(pos)
        if item is None:
            return
        kind, oid = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        if kind == "group":
            menu.addAction("重命名组", lambda: self._rename_group(oid, item))
            menu.addAction("删除组(仅限空组)", lambda: self._delete_group(oid))
        else:  # account
            menu.addAction("重命名账号", lambda: self._rename_account(oid, item))
            menu.addAction("移动到其他组", lambda: self._move_account(oid))
            menu.addSeparator()
            menu.addAction("删除账号(连同 Profile)", lambda: self._delete_account(oid))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _rename_group(self, group_id: int, _item):
        cur = next((g["name"] for g in self._store.list_groups() if g["id"] == group_id), "")
        new, ok = QInputDialog.getText(self, "重命名组", "新组名:", text=cur)
        if ok and new.strip():
            self._store.rename_group(group_id, new.strip())
            self._refresh_tree()

    def _delete_group(self, group_id: int):
        try:
            self._store.delete_group(group_id)
        except ValueError as e:
            QMessageBox.warning(self, "无法删除", str(e))
            return
        self._refresh_tree()

    def _rename_account(self, account_id: int, _item):
        cur = next((a["display_name"] for a in self._store.list_accounts() if a["id"] == account_id), "")
        new, ok = QInputDialog.getText(self, "重命名账号", "新名称:", text=cur)
        if ok and new.strip():
            self._store.update_account_display_name(account_id, new.strip())
            self._refresh_tree()

    def _move_account(self, account_id: int):
        gid = self._pick_group_id()
        if gid is None:
            return
        self._store.move_account_to_group(account_id, gid)
        self._refresh_tree()

    def _delete_account(self, account_id: int):
        ok = QMessageBox.question(
            self, "确认删除",
            "将同时删除该账号的本地 Profile 数据，无法恢复。是否继续？",
        )
        if ok != QMessageBox.Yes:
            return
        try:
            self._mgr.delete_account_with_files(account_id)
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"{type(e).__name__}: {e}")
            return
        self._refresh_tree()

    # ---- double-click → open creator backend ----
    def _on_double_click(self, item: QTreeWidgetItem, _col: int):
        data = item.data(0, Qt.UserRole)
        if not data or data[0] != "account":
            return
        account_id = data[1]
        acc = next((a for a in self._store.list_accounts() if a["id"] == account_id), None)
        if not acc:
            return
        pub = self._publishers.get(acc["platform"])
        if not pub or not pub.creator_home_url:
            QMessageBox.warning(self, "无法打开", f"未配置 {acc['platform']} 的创作者后台 URL")
            return
        self._launcher.open_creator_backend(acc["profile_path"], pub.creator_home_url)
