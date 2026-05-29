"""
voice_selector_dialog.py - 音色选择对话框
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.theme import Theme, Typography
from core.config import config

VOICE_LIST = [
    {"id": "zh_female_vv_uranus_bigtts",           "name": "Vivi 2.0",     "desc": "清晰标准女声"},
    {"id": "zh_female_xiaohe_uranus_bigtts",      "name": "小何 2.0",      "desc": "温柔女声"},
    {"id": "zh_male_m191_uranus_bigtts",          "name": "云舟 2.0",      "desc": "成熟男声"},
    {"id": "zh_male_taocheng_uranus_bigtts",      "name": "小天 2.0",      "desc": "青年男声"},
    {"id": "zh_male_liufei_uranus_bigtts",        "name": "刘飞 2.0",      "desc": "活力男声"},
    {"id": "zh_male_sophie_uranus_bigtts",        "name": "魅力苏菲 2.0",  "desc": "知性女声"},
    {"id": "zh_male_sunwukong_uranus_bigtts",      "name": "孙悟空 2.0",    "desc": "活泼男声"},
    {"id": "zh_female_baiyutang_uranus_bigtts",    "name": "白玉堂 2.0",    "desc": "清冷女声"},
    {"id": "zh_male_zhugeliang_uranus_bigtts",     "name": "诸葛亮 2.0",    "desc": "智慧男声"},
    {"id": "zh_female_xiaoyan_uranus_bigtts",      "name": "小燕 2.0",      "desc": "甜美女声"},
    {"id": "zh_male_sandy_uranus_bigtts",          "name": "Sandy 2.0",     "desc": "沉稳男声"},
    {"id": "zh_female_zhimeng_uranus_bigtts",      "name": "知梦 2.0",      "desc": "温柔女声"},
    {"id": "zh_male_dongdong_uranus_bigtts",        "name": "东东 2.0",      "desc": "正太男声"},
    {"id": "zh_female_youyou_uranus_bigtts",       "name": "悠悠 2.0",      "desc": "可爱女声"},
    {"id": "zh_female_xiaowanzi_uranus_bigtts",    "name": "小丸子 2.0",    "desc": "活力女声"},
    {"id": "zh_female_luna_uranus_bigtts",          "name": "Luna 2.0",      "desc": "神秘女声"},
    {"id": "zh_male_dayi_uranus_bigtts",            "name": "大壹 2.0",      "desc": "大气男声"},
    {"id": "zh_female_heimaozhentan_uranus_bigtts", "name": "黑猫侦探社咪仔 2.0", "desc": "可爱女声"},
    {"id": "zh_female_jitangnv_uranus_bigtts",     "name": "鸡汤女 2.0",     "desc": "温暖女声"},
    {"id": "zh_female_meilinvyou_uranus_bigtts",    "name": "魅力女友 2.0",   "desc": "温柔女声"},
    {"id": "zh_female_liuchangnv_uranus_bigtts",    "name": "流畅女声 2.0",   "desc": "自然女声"},
    {"id": "zh_male_ruyayichen_uranus_bigtts",      "name": "儒雅逸辰 2.0",   "desc": "儒雅男声"},
    {"id": "en_male_tim_uranus_bigtts",             "name": "Tim",          "desc": "英文男声"},
    {"id": "en_female_dacey_uranus_bigtts",          "name": "Dacey",        "desc": "英文女声"},
    {"id": "en_female_stokie_uranus_bigtts",         "name": "Stokie",       "desc": "英文女声"},
]


class VoiceSelectorDialog(QDialog):
    voice_selected = pyqtSignal(str)

    def __init__(self, current_voice: str = "", parent=None):
        super().__init__(parent)
        self.current_voice = current_voice
        self.selected_voice = current_voice
        self.setWindowTitle("选择音色")
        self.setFixedSize(480, 480)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setStyleSheet(f"background-color: {Theme.BG_BASE};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("选择 TTS 音色")
        title.setStyleSheet(
            f"font-size: {Typography.SIZE_LG}px; "
            f"font-weight: {Typography.WEIGHT_BOLD}; "
            f"color: {Theme.TEXT_PRIMARY};"
        )
        layout.addWidget(title)

        search = QLineEdit()
        search.setPlaceholderText("搜索音色…")
        search.setStyleSheet(
            f"background: {Theme.BG_ELEVATED}; "
            f"color: {Theme.TEXT_PRIMARY}; "
            f"border: 1px solid {Theme.BORDER_LIGHT}; "
            f"border-radius: 6px; padding: 8px; "
            f"font-size: {Typography.SIZE_SM}px;"
        )
        layout.addWidget(search)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            f"background: {Theme.BG_ELEVATED}; "
            f"border: 1px solid {Theme.BORDER_LIGHT}; "
            f"border-radius: 6px;"
        )
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(
            f"background: {Theme.BG_ELEVATED}; color: {Theme.TEXT_PRIMARY}; "
            f"border: 1px solid {Theme.BORDER_LIGHT}; border-radius: 6px; padding: 6px 16px;"
        )
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("确认")
        ok_btn.clicked.connect(self._on_confirm)
        ok_btn.setStyleSheet(
            f"background: {Theme.ACCENT_PRIMARY}; color: white; "
            f"border: none; border-radius: 6px; padding: 6px 16px;"
        )
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self._populate_list()
        search.textChanged.connect(self._filter)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)

    def _populate_list(self, filter_text: str = ""):
        self.list_widget.clear()
        for v in VOICE_LIST:
            label = f"{v['name']}  {v['desc']}"
            if filter_text and filter_text.lower() not in label.lower():
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, v['id'])
            if v['id'] == self.current_voice:
                item.setSelected(True)
            self.list_widget.addItem(item)

    def _filter(self, text: str):
        self._populate_list(text)

    def _on_confirm(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_voice = item.data(Qt.UserRole)
            self.voice_selected.emit(self.selected_voice)
        self.accept()

    def _on_double_click(self, item):
        self.selected_voice = item.data(Qt.UserRole)
        self.voice_selected.emit(self.selected_voice)
        self.accept()
