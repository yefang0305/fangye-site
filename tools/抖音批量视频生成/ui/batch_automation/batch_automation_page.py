"""
batch_automation_page.py
─────────────────────────
批量自动化工作台

工作流（每条脚本）：
  LLM 重写 → [人工审核，可选] → TTS 合成 → 按文案分段 → 导出视频

依赖：
  - TTSWorker / ComposeWorker  (从 main_desktop 传入，避免循环 import)
  - LLMThread / CoverImageThread (本模块内定义)
  - segment_by_text            (core.text_segmenter)
  - config                     (core.config)
  - auto_save / auto_save_audio (core.auto_saver)
"""

import os
import json
import logging
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QSplitter, QScrollArea,
    QComboBox, QCheckBox, QSpinBox, QAbstractItemView,
)

from core.config import config
from core.auto_saver import auto_save, auto_save_audio
from core.text_segmenter import segment_by_text
from ui.theme import Theme, Typography, Spacing
from ui.voice_selector_dialog import VOICE_LIST

logger = logging.getLogger('BatchAutomation')

CHAT_URL = 'https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions'

JSON_SUFFIX = """

---
⚠ 【强制输出要求，必须严格遵守，否则返回无效】
1. rewritten 字段为改写后的完整文案，段落之间不得有空白行，所有内容连续排列；
2. title 字段为视频标题，用于视频文件命名，要求提炼文案的中心思想，简洁准确，总字数不超过20字；
3. cover_text 字段为封面文字，要求提炼整个文案中的重点词，仅限2-4个字，用于封面竖排展示；
4. 必须返回纯JSON格式，不要加任何其他内容（不要解释、不要说明、不要markdown标记、不要代码块、不要前后多余的文字），直接输出JSON：
{"rewritten": "改写后的完整文案（无空白行）", "title": "视频标题（20字以内）", "cover_text": "封面重点词（2-4字）"}
"""

# ── State constants
ST_PENDING  = 'pending'
ST_LLM      = 'llm'
ST_REVIEW   = 'review'
ST_TTS      = 'tts'
ST_SEGMENT  = 'segment'
ST_COMPOSE  = 'compose'
ST_DONE     = 'done'
ST_FAILED   = 'failed'
ST_SKIPPED  = 'skipped'
ST_COVER    = 'cover'
ST_RENAME   = 'rename'

STATE_LABEL = {
    ST_PENDING:  '等待中',
    ST_LLM:      '⏳ LLM 生成…',
    ST_REVIEW:   '👁 待审核',
    ST_TTS:      '⏳ 生成音频…',
    ST_SEGMENT:  '⏳ 分段中…',
    ST_COMPOSE:  '⏳ 合成视频…',
    ST_DONE:     '✅ 完成',
    ST_FAILED:   '❌ 失败',
    ST_SKIPPED:  '⏭ 跳过',
    ST_COVER:    '⏳ 等待封面…',
    ST_RENAME:   '⏳ 插入封面…',
}

STATE_COLOR = {
    ST_PENDING:  '#888888',
    ST_LLM:      '#4a9eff',
    ST_REVIEW:   '#f0a500',
    ST_TTS:      '#4a9eff',
    ST_SEGMENT:  '#4a9eff',
    ST_COMPOSE:  '#4a9eff',
    ST_DONE:     '#52c41a',
    ST_FAILED:   '#ff4d4f',
    ST_SKIPPED:  '#888888',
    ST_COVER:    '#4a9eff',
    ST_RENAME:   '#4a9eff',
}


# ── LLM Thread
class LLMThread(QThread):
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, api_key, model, skill_prompt, source_text, parent=None):
        super().__init__(parent)
        self.api_key      = api_key
        self.model        = model
        self.skill_prompt = skill_prompt
        self.source_text  = source_text

    def run(self):
        import requests
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': self.skill_prompt},
                {'role': 'user',   'content': self.source_text},
            ],
            'temperature': 0.85,
            'max_tokens': 4096,
        }
        try:
            resp = requests.post(CHAT_URL, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                text = (resp.json()
                        .get('choices', [{}])[0]
                        .get('message', {})
                        .get('content', '')
                        .strip())
                if text:
                    self.finished.emit(text)
                else:
                    self.error.emit('模型返回内容为空，请重试')
            else:
                self.error.emit(f'API 错误 HTTP {resp.status_code}：{resp.text[:200]}')
        except Exception as e:
            self.error.emit(f'请求异常：{e}')


# ── CoverImageThread
class CoverImageThread(QThread):
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, prompt: str, width: int, height: int, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.width  = width
        self.height = height

    def run(self):
        """封面图生成（需要图像生成 API 配置，未配置时静默失败）"""
        try:
            from core.image_gen.api_client import APIClient
        except ImportError:
            self.error.emit('图像生成模块未安装（core.image_gen.api_client）')
            return

        from core.config import config as _cfg
        import time

        access_key = _cfg.get('image_access_key', '')
        secret_key = _cfg.get('image_secret_key', '')
        model = _cfg.get('image_model', 'jimeng_t2i_v40')

        if not access_key or not secret_key:
            self.error.emit('未配置图像生成 AccessKey/SecretKey')
            return

        try:
            client = APIClient(access_key, secret_key)
            image_data, err = client.generate_image(self.prompt, model, self.width, self.height)
            if err:
                self.error.emit(f'文生图失败：{err}')
                return
            out_dir = Path('output/covers')
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = f"cover_{int(time.time())}.png"
            fpath = out_dir / fname
            with open(fpath, 'wb') as f:
                f.write(image_data)
            self.finished.emit(str(fpath))
        except Exception as e:
            self.error.emit(f'封面生成异常：{e}')


# ── ScriptItem
class ScriptItem:
    def __init__(self, source_text: str):
        self.source_text  = source_text.strip()
        self.rewritten    = ''
        self.audio_path   = ''
        self.timestamps   = []
        self.duration     = 0.0
        self.segments     = []
        self.output_paths = []
        self.state        = ST_PENDING
        self.error_msg    = ''
        self.title            = ''
        self.cover_text       = ''
        self.cover_prompt     = ''
        self.cover_image_path = ''
        self.cover_ready      = False
        self._pending_compose_paths = []
        self.retry_count  = 0
        self.dispatched   = False


MAX_GEN_RETRIES = 3


# ── ScriptItemWidget
class ScriptItemWidget(QWidget):
    def __init__(self, index: int, text: str, parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        self.idx_label = QLabel(f"{index + 1:02d}")
        self.idx_label.setFixedWidth(26)
        self.idx_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.idx_label.setStyleSheet(
            f"color: {Theme.TEXT_TERTIARY}; font-size: {Typography.SIZE_SM}px; "
            f"font-weight: {Typography.WEIGHT_MEDIUM}; padding-top: 2px;"
        )
        root.addWidget(self.idx_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setContentsMargins(0, 0, 0, 0)

        clean = text.replace('\n', ' ').strip()
        line1 = clean[:40] + ('…' if len(clean) > 40 else '')
        self.line1_label = QLabel(line1)
        self.line1_label.setStyleSheet(
            f"color: {Theme.TEXT_PRIMARY}; font-size: {Typography.SIZE_SM}px;"
        )
        text_col.addWidget(self.line1_label)

        if len(clean) > 40:
            line2 = clean[40:80] + ('…' if len(clean) > 80 else '')
            self.line2_label = QLabel(line2)
            self.line2_label.setStyleSheet(
                f"color: {Theme.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px;"
            )
            text_col.addWidget(self.line2_label)

        root.addLayout(text_col, 1)

        self.state_label = QLabel(STATE_LABEL[ST_PENDING])
        self.state_label.setFixedWidth(96)
        self.state_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.state_label.setWordWrap(True)
        self.state_label.setStyleSheet(
            f"color: {STATE_COLOR[ST_PENDING]}; font-size: {Typography.SIZE_XS}px;"
        )
        root.addWidget(self.state_label)

    def set_state(self, state: str, extra: str = ''):
        label = STATE_LABEL.get(state, state)
        if extra:
            label = extra
        self.state_label.setText(label)
        color = STATE_COLOR.get(state, Theme.TEXT_SECONDARY)
        self.state_label.setStyleSheet(
            f"color: {color}; font-size: {Typography.SIZE_XS}px;"
        )


# ── DropListWidget
class DropListWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                local = url.toLocalFile()
                if local.lower().endswith(('.txt', '.json')):
                    paths.append(local)
            if paths:
                self.files_dropped.emit(sorted(paths))
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


# ── BatchAutomationPage
class BatchAutomationPage(QWidget):

    SLOTS_PER_DAY = 3
    SLOT_LEAD_HOURS = 2

    def __init__(self, tts_worker_class, compose_worker_class, parent=None):
        super().__init__(parent)
        self.TTSWorker     = tts_worker_class
        self.ComposeWorker = compose_worker_class

        self._queue: list[ScriptItem] = []
        self._item_widgets: list[ScriptItemWidget] = []
        self._current_idx       = -1
        self._current_llm_ver   = 0
        self._running       = False
        self._paused        = False
        self._skill_prompt  = ''
        self._skill_path    = ''
        self._llm_thread    = None
        self._tts_worker    = None
        self._compose_worker = None
        self._cover_thread  = None

        self._init_ui()
        self._restore_defaults()

    # ── UI ──

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("批量自动化工作台")
        title.setStyleSheet(
            f"font-size: {Typography.SIZE_XL}px; "
            f"font-weight: {Typography.WEIGHT_BOLD}; "
            f"color: {Theme.TEXT_PRIMARY};"
        )
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: " + Theme.BORDER_LIGHT + "; }")

        left = self._build_queue_panel()
        splitter.addWidget(left)
        mid = self._build_params_panel()
        splitter.addWidget(mid)
        right = self._build_log_panel()
        splitter.addWidget(right)

        splitter.setSizes([380, 280, 340])
        root.addWidget(splitter, 1)

    # ── 左栏 ──

    def _build_queue_panel(self) -> QWidget:
        panel = self._make_panel("脚本队列")
        body  = panel.layout()

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        import_txt_btn = self._small_btn("📄 导入 TXT")
        import_txt_btn.setToolTip("选择一个或多个 .txt 文件，每个文件作为一条脚本导入")
        import_txt_btn.clicked.connect(self._on_import_txt)
        toolbar.addWidget(import_txt_btn)

        import_btn = self._small_btn("📂 导入 JSON")
        import_btn.setToolTip("导入包含多条文案的 JSON 文件（格式：[\"文案1\", \"文案2\", ...]）")
        import_btn.clicked.connect(self._on_import_json)
        toolbar.addWidget(import_btn)

        add_btn = self._small_btn("＋ 手动添加")
        add_btn.clicked.connect(self._on_add_manual)
        toolbar.addWidget(add_btn)

        del_btn = self._small_btn("🗑 删除选中")
        del_btn.clicked.connect(self._on_delete_selected)
        toolbar.addWidget(del_btn)

        clear_btn = self._small_btn("清空")
        clear_btn.clicked.connect(self._on_clear_queue)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()
        body.addLayout(toolbar)

        self.queue_list = DropListWidget()
        self.queue_list.files_dropped.connect(self._on_files_dropped)
        self.queue_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.queue_list.setStyleSheet(f"""
            QListWidget {{
                background: {Theme.BG_ELEVATED};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
            }}
            QListWidget::item {{ border-bottom: 1px solid {Theme.BORDER_LIGHT}; padding: 2px; }}
            QListWidget::item:selected {{ background: {Theme.SIDEBAR_ITEM_ACTIVE}; }}
        """)
        body.addWidget(self.queue_list)

        self.queue_count_label = QLabel("共 0 条脚本")
        self.queue_count_label.setStyleSheet(
            f"color: {Theme.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px;"
        )
        body.addWidget(self.queue_count_label)

        return panel

    # ── 中栏 ──

    def _build_params_panel(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background: transparent;")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(10)

        t = QLabel("全局参数")
        t.setStyleSheet(
            f"font-size: {Typography.SIZE_MD}px; "
            f"font-weight: {Typography.WEIGHT_MEDIUM}; "
            f"color: {Theme.TEXT_PRIMARY};"
        )
        layout.addWidget(t)

        # SKILL
        sk_panel = self._make_panel("SKILL 文件")
        sk_body  = sk_panel.layout()

        self.skill_label = QLabel("未加载")
        self.skill_label.setWordWrap(True)
        self.skill_label.setStyleSheet(
            f"color: {Theme.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px;"
        )
        sk_body.addWidget(self.skill_label)

        skill_btn = self._small_btn("📂 选择 SKILL")
        skill_btn.clicked.connect(self._on_select_skill)
        sk_body.addWidget(skill_btn)

        layout.addWidget(sk_panel)

        # TTS
        tts_panel = self._make_panel("语音合成")
        tts_body  = tts_panel.layout()

        r_voice = QHBoxLayout()
        r_voice.addWidget(QLabel("音色"))
        self.voice_combo = QComboBox()
        current_voice = config.get('tts_voice', '')
        for v in VOICE_LIST:
            self.voice_combo.addItem(f"{v['name']}  {v['desc']}", userData=v['id'])
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == current_voice:
                self.voice_combo.setCurrentIndex(i)
                break
        self.voice_combo.setStyleSheet(self._combo_style())
        r_voice.addWidget(self.voice_combo, 1)
        tts_body.addLayout(r_voice)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("语速"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(50, 200)
        self.speed_spin.setValue(int(config.get('tts_speed', 1.0) * 100))
        self.speed_spin.setSuffix('%')
        self.speed_spin.setFixedWidth(72)
        self.speed_spin.setStyleSheet(self._spin_style())
        r1.addWidget(self.speed_spin)
        r1.addStretch()
        tts_body.addLayout(r1)

        r_vol = QHBoxLayout()
        r_vol.addWidget(QLabel("音量"))
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(50, 200)
        self.volume_spin.setValue(int(config.get('tts_volume', 100)))
        self.volume_spin.setSuffix('%')
        self.volume_spin.setFixedWidth(72)
        self.volume_spin.setStyleSheet(self._spin_style())
        self.volume_spin.valueChanged.connect(lambda v: config.set('tts_volume', v))
        r_vol.addWidget(self.volume_spin)
        r_vol.addStretch()
        tts_body.addLayout(r_vol)

        layout.addWidget(tts_panel)

        # 分段
        seg_panel = self._make_panel("分段设置")
        seg_body  = seg_panel.layout()

        r_mode = QHBoxLayout()
        r_mode.addWidget(QLabel("分段模式"))
        self.seg_mode_combo = QComboBox()
        self.seg_mode_combo.addItem("按文案分段", userData='text')
        self.seg_mode_combo.addItem("按时长均分", userData='duration')
        self.seg_mode_combo.addItem("按数量均分", userData='count')
        self.seg_mode_combo.setStyleSheet(self._combo_style())
        self.seg_mode_combo.currentIndexChanged.connect(self._on_seg_mode_changed)
        r_mode.addWidget(self.seg_mode_combo, 1)
        seg_body.addLayout(r_mode)

        self.seg_text_widget = QWidget()
        seg_text_layout = QHBoxLayout(self.seg_text_widget)
        seg_text_layout.setContentsMargins(0, 0, 0, 0)
        seg_text_layout.addWidget(QLabel("最短段落时长"))
        self.min_dur_spin = QSpinBox()
        self.min_dur_spin.setRange(5, 100)
        self.min_dur_spin.setValue(int(config.get('text_segment_min_duration', 1.8) * 10))
        self.min_dur_spin.setSuffix(' × 0.1s')
        self.min_dur_spin.setFixedWidth(90)
        self.min_dur_spin.setStyleSheet(self._spin_style())
        self.min_dur_spin.valueChanged.connect(
            lambda v: config.set('text_segment_min_duration', round(v / 10.0, 1))
        )
        seg_text_layout.addWidget(self.min_dur_spin)
        seg_text_layout.addStretch()
        seg_body.addWidget(self.seg_text_widget)

        self.seg_dur_widget = QWidget()
        seg_dur_layout = QHBoxLayout(self.seg_dur_widget)
        seg_dur_layout.setContentsMargins(0, 0, 0, 0)
        seg_dur_layout.addWidget(QLabel("每段时长"))
        self.seg_dur_spin = QSpinBox()
        self.seg_dur_spin.setRange(1, 60)
        self.seg_dur_spin.setValue(config.get('batch_duration_seconds', 5))
        self.seg_dur_spin.setSuffix(' 秒')
        self.seg_dur_spin.setFixedWidth(72)
        self.seg_dur_spin.setStyleSheet(self._spin_style())
        seg_dur_layout.addWidget(self.seg_dur_spin)
        seg_dur_layout.addStretch()
        self.seg_dur_widget.hide()
        seg_body.addWidget(self.seg_dur_widget)

        self.seg_count_widget = QWidget()
        seg_count_layout = QHBoxLayout(self.seg_count_widget)
        seg_count_layout.setContentsMargins(0, 0, 0, 0)
        seg_count_layout.addWidget(QLabel("分段数量"))
        self.seg_count_spin = QSpinBox()
        self.seg_count_spin.setRange(1, 20)
        self.seg_count_spin.setValue(config.get('batch_average_count', 4))
        self.seg_count_spin.setSuffix(' 段')
        self.seg_count_spin.setFixedWidth(68)
        self.seg_count_spin.setStyleSheet(self._spin_style())
        seg_count_layout.addWidget(self.seg_count_spin)
        seg_count_layout.addStretch()
        self.seg_count_widget.hide()
        seg_body.addWidget(self.seg_count_widget)

        layout.addWidget(seg_panel)

        # 素材
        mat_panel = self._make_panel("素材文件夹")
        mat_body  = mat_panel.layout()

        self.material_label = QLabel("未设置")
        self.material_label.setWordWrap(True)
        self.material_label.setStyleSheet(
            f"color: {Theme.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px;"
        )
        mat_body.addWidget(self.material_label)

        mat_btn = self._small_btn("📂 选择素材文件夹")
        mat_btn.clicked.connect(self._on_select_material)
        mat_body.addWidget(mat_btn)

        self._material_folder = config.get('default_material_folder', '')
        if self._material_folder:
            self.material_label.setText(Path(self._material_folder).name)
            self.material_label.setStyleSheet(
                f"color: {Theme.SUCCESS_TEXT}; font-size: {Typography.SIZE_XS}px;"
            )

        layout.addWidget(mat_panel)

        # BGM
        bgm_panel = self._make_panel("BGM 文件夹")
        bgm_body  = bgm_panel.layout()

        self.bgm_label = QLabel("未设置")
        self.bgm_label.setWordWrap(True)
        self.bgm_label.setStyleSheet(
            f"color: {Theme.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px;"
        )
        bgm_body.addWidget(self.bgm_label)

        bgm_btn = self._small_btn("📂 选择 BGM 文件夹")
        bgm_btn.clicked.connect(self._on_select_bgm)
        bgm_body.addWidget(bgm_btn)

        r_vol2 = QHBoxLayout()
        r_vol2.addWidget(QLabel("BGM 音量"))
        self.bgm_vol_spin = QSpinBox()
        self.bgm_vol_spin.setRange(0, 100)
        self.bgm_vol_spin.setValue(config.get('bgm_volume', 30))
        self.bgm_vol_spin.setSuffix('%')
        self.bgm_vol_spin.setFixedWidth(68)
        self.bgm_vol_spin.setStyleSheet(self._spin_style())
        self.bgm_vol_spin.valueChanged.connect(lambda v: config.set('bgm_volume', v))
        r_vol2.addWidget(self.bgm_vol_spin)
        r_vol2.addStretch()
        bgm_body.addLayout(r_vol2)

        self._bgm_folder = config.get('default_bgm_folder', '')
        self._bgm_files  = []
        if self._bgm_folder and Path(self._bgm_folder).is_dir():
            self._bgm_files = self._scan_bgm(self._bgm_folder)
            self.bgm_label.setText(f"{Path(self._bgm_folder).name}  ({len(self._bgm_files)} 首)")
            self.bgm_label.setStyleSheet(
                f"color: {Theme.SUCCESS_TEXT}; font-size: {Typography.SIZE_XS}px;"
            )

        layout.addWidget(bgm_panel)

        # 输出
        out_panel = self._make_panel("输出设置")
        out_body  = out_panel.layout()

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("分辨率"))
        self.res_combo = QComboBox()
        self.res_combo.addItems(["1080x1920", "720x1280", "1920x1080", "1280x720"])
        saved_res = config.get('output_resolution', '1080x1920')
        idx = self.res_combo.findText(saved_res)
        if idx >= 0:
            self.res_combo.setCurrentIndex(idx)
        self.res_combo.setStyleSheet(self._combo_style())
        self.res_combo.currentTextChanged.connect(lambda v: config.set('output_resolution', v))
        r3.addWidget(self.res_combo)
        r3.addStretch()
        out_body.addLayout(r3)

        r4a = QHBoxLayout()
        r4a.addWidget(QLabel("文案版本数"))
        self.llm_ver_spin = QSpinBox()
        self.llm_ver_spin.setRange(1, 5)
        self.llm_ver_spin.setValue(1)
        self.llm_ver_spin.setFixedWidth(56)
        self.llm_ver_spin.setToolTip("每条原文案调用 LLM 生成几个不同版本")
        self.llm_ver_spin.setStyleSheet(self._spin_style())
        r4a.addWidget(self.llm_ver_spin)
        r4a.addStretch()
        out_body.addLayout(r4a)

        r4 = QHBoxLayout()
        r4.addWidget(QLabel("每版本视频数"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 10)
        self.count_spin.setValue(1)
        self.count_spin.setFixedWidth(56)
        self.count_spin.setToolTip("同一段音频用不同素材随机剪辑，生成几个不同画面的视频")
        self.count_spin.setStyleSheet(self._spin_style())
        r4.addWidget(self.count_spin)
        r4.addStretch()
        out_body.addLayout(r4)

        r5 = QHBoxLayout()
        r5.addWidget(QLabel("输出目录"))
        self.output_label = QLabel(config.get('output_dir', './output/'))
        self.output_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: {Typography.SIZE_XS}px;"
        )
        r5.addWidget(self.output_label, 1)
        out_dir_btn = self._small_btn("…")
        out_dir_btn.setFixedWidth(28)
        out_dir_btn.clicked.connect(self._on_select_output_dir)
        r5.addWidget(out_dir_btn)
        out_body.addLayout(r5)

        r6 = QHBoxLayout()
        r6.addWidget(QLabel("封面底图"))
        default_cover = config.get('cover_bg_path', '')
        self.cover_label = QLabel(Path(default_cover).name if default_cover and Path(default_cover).exists() else "未设置")
        self.cover_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: {Typography.SIZE_XS}px;"
        )
        self._cover_bg_path = default_cover if default_cover and Path(default_cover).exists() else ''
        r6.addWidget(self.cover_label, 1)
        cover_btn = self._small_btn("…")
        cover_btn.setFixedWidth(28)
        cover_btn.clicked.connect(self._on_select_cover_bg)
        r6.addWidget(cover_btn)
        out_body.addLayout(r6)

        layout.addWidget(out_panel)

        # 审核
        review_panel = self._make_panel("执行选项")
        review_body  = review_panel.layout()

        self.review_check = QCheckBox("LLM 生成后人工审核")
        self.review_check.setChecked(False)
        self.review_check.setStyleSheet(
            f"color: {Theme.TEXT_PRIMARY}; font-size: {Typography.SIZE_SM}px;"
        )
        review_body.addWidget(self.review_check)

        review_tip = QLabel("勾选后每条脚本 LLM 生成完成会暂停，\n需手动点击「继续」才会进入 TTS 步骤。")
        review_tip.setWordWrap(True)
        review_tip.setStyleSheet(
            f"color: {Theme.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px;"
        )
        review_body.addWidget(review_tip)

        layout.addWidget(review_panel)
        layout.addStretch()

        scroll_area.setWidget(inner)
        return scroll_area

    # ── 右栏 ──

    def _build_log_panel(self) -> QWidget:
        panel = self._make_panel("执行日志")
        body  = panel.layout()

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
                font-size: {Typography.SIZE_SM}px;
                padding: 6px;
                font-family: Consolas, monospace;
            }}
        """)
        body.addWidget(self.log_edit)

        self.review_frame = QFrame()
        self.review_frame.setStyleSheet(f"""
            QFrame {{
                background: {Theme.BG_ELEVATED};
                border: 1px solid {Theme.ACCENT_PRIMARY};
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
                padding: 4px;
            }}
        """)
        review_layout = QVBoxLayout(self.review_frame)
        review_layout.setContentsMargins(8, 8, 8, 8)
        review_layout.setSpacing(6)

        review_title = QLabel("👁 请审核 LLM 生成结果（可直接编辑）")
        review_title.setStyleSheet(
            f"color: {Theme.ACCENT_PRIMARY}; font-size: {Typography.SIZE_SM}px; "
            f"font-weight: {Typography.WEIGHT_MEDIUM}; border: none;"
        )
        review_layout.addWidget(review_title)

        self.review_edit = QTextEdit()
        self.review_edit.setMaximumHeight(160)
        self.review_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {Theme.BG_SURFACE};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
                font-size: {Typography.SIZE_SM}px;
                padding: 6px;
            }}
        """)
        review_layout.addWidget(self.review_edit)

        review_btn_row = QHBoxLayout()
        review_btn_row.setSpacing(8)

        self.review_continue_btn = QPushButton("✅ 确认继续")
        self.review_continue_btn.setStyleSheet(self._primary_btn_style())
        self.review_continue_btn.clicked.connect(self._on_review_continue)
        review_btn_row.addWidget(self.review_continue_btn)

        self.review_skip_btn = QPushButton("⏭ 跳过此条")
        self.review_skip_btn.setStyleSheet(self._secondary_btn_style())
        self.review_skip_btn.clicked.connect(self._on_review_skip)
        review_btn_row.addWidget(self.review_skip_btn)

        review_layout.addLayout(review_btn_row)
        self.review_frame.hide()
        body.addWidget(self.review_frame)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.start_btn = QPushButton("▶ 开始执行")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet(self._primary_btn_style())
        self.start_btn.clicked.connect(self._on_start)
        ctrl_row.addWidget(self.start_btn)

        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setFixedHeight(40)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet(self._secondary_btn_style())
        self.pause_btn.clicked.connect(self._on_pause)
        ctrl_row.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹ 终止")
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self._secondary_btn_style())
        self.stop_btn.clicked.connect(self._on_stop)
        ctrl_row.addWidget(self.stop_btn)

        body.addLayout(ctrl_row)

        open_row = QHBoxLayout()
        open_row.setSpacing(8)

        self.open_output_btn = QPushButton("📁 打开输出目录")
        self.open_output_btn.setFixedHeight(32)
        self.open_output_btn.setStyleSheet(self._secondary_btn_style())
        self.open_output_btn.clicked.connect(self._on_open_output)
        open_row.addWidget(self.open_output_btn)

        self.send_publish_btn = QPushButton("📤 发送到待发布队列")
        self.send_publish_btn.setFixedHeight(32)
        self.send_publish_btn.setToolTip("将所有已完成视频复制到 to_publish/ 目录")
        self.send_publish_btn.setStyleSheet(self._primary_btn_style())
        self.send_publish_btn.clicked.connect(self._on_send_to_publish)
        open_row.addWidget(self.send_publish_btn)

        body.addLayout(open_row)

        return panel

    # ── 队列操作 ──

    def _on_import_txt(self):
        default_dir = config.get('default_material_folder') or os.path.expanduser('~')
        paths, _ = QFileDialog.getOpenFileNames(
            self, '导入 TXT 文件', default_dir,
            'TXT 文件 (*.txt);;所有文件 (*.*)'
        )
        if paths:
            self._load_txt_files(sorted(paths))

    def _on_files_dropped(self, paths: list):
        txt_files  = [p for p in paths if p.lower().endswith('.txt')]
        json_files = [p for p in paths if p.lower().endswith('.json')]
        if txt_files:
            self._load_txt_files(txt_files)
        for p in json_files:
            self._load_json_file(p)

    def _load_txt_files(self, paths: list):
        loaded = 0
        for p in paths:
            try:
                text = Path(p).read_text(encoding='utf-8').strip()
                if not text:
                    self._log(f'⚠ 跳过空文件：{Path(p).name}')
                    continue
                self._add_script(text)
                loaded += 1
            except Exception as e:
                self._log(f'⚠ 读取失败 {Path(p).name}：{e}')
        if loaded:
            self._log(f'已导入 {loaded} 个 TXT 文件')

    def _load_json_file(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                QMessageBox.warning(self, '格式错误', f'{Path(path).name}\nJSON 文件应为列表格式')
                return
            texts = [str(x).strip() for x in data if str(x).strip()]
            for t in texts:
                self._add_script(t)
            self._log(f'已导入 {len(texts)} 条脚本（{Path(path).name}）')
        except Exception as e:
            QMessageBox.critical(self, '读取失败', f'无法读取 JSON 文件：\n{e}')

    def _on_import_json(self):
        default_dir = os.path.expanduser('~')
        path, _ = QFileDialog.getOpenFileName(
            self, '导入脚本 JSON', default_dir,
            'JSON 文件 (*.json);;所有文件 (*.*)'
        )
        if not path:
            return
        self._load_json_file(path)

    def _on_add_manual(self):
        dlg = _InputDialog(self)
        if dlg.exec_():
            text = dlg.get_text()
            if text:
                self._add_script(text)

    def _on_delete_selected(self):
        rows = sorted(set(i.row() for i in self.queue_list.selectedIndexes()), reverse=True)
        for row in rows:
            self.queue_list.takeItem(row)
            self._queue.pop(row)
            self._item_widgets.pop(row)
        for i, w in enumerate(self._item_widgets):
            w.idx_label.setText(f"{i + 1:02d}")
        self._update_count()

    def _on_clear_queue(self):
        if self._running:
            QMessageBox.warning(self, '执行中', '请先终止执行再清空队列')
            return
        self.queue_list.clear()
        self._queue.clear()
        self._item_widgets.clear()
        self._update_count()

    @staticmethod
    def _clean_script(text: str) -> str:
        import re, json as _json
        t = text.strip()
        t = re.sub(r'^```(?:json)?\s*', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\s*```$', '', t).strip()
        if t.startswith('{'):
            try:
                obj = _json.loads(t)
                for key in ('rewritten', 'content', 'text', 'result', 'output'):
                    if key in obj and isinstance(obj[key], str):
                        return obj[key].strip()
            except Exception:
                pass
        return t

    def _add_script(self, text: str):
        text = self._clean_script(text)
        if not text:
            return
        item_data = ScriptItem(text)
        self._queue.append(item_data)

        idx = len(self._queue) - 1
        widget = ScriptItemWidget(idx, text)
        self._item_widgets.append(widget)

        from PyQt5.QtCore import QSize
        list_item = QListWidgetItem()
        height = 68 if len(text.replace('\n', ' ').strip()) > 40 else 48
        list_item.setSizeHint(QSize(0, height))
        self.queue_list.addItem(list_item)
        self.queue_list.setItemWidget(list_item, widget)

        self._update_count()

    def add_scripts_from_library(self, scripts: list[str]):
        added = 0
        for text in scripts:
            before = len(self._queue)
            self._add_script(text)
            if len(self._queue) > before:
                added += 1
        if added:
            self._log(f'已从文案库导入 {added} 条脚本')
        return added

    def _update_count(self):
        self.queue_count_label.setText(f"共 {len(self._queue)} 条脚本")

    # ── 参数 ──

    def _on_seg_mode_changed(self, _):
        mode = self.seg_mode_combo.currentData()
        self.seg_text_widget.setVisible(mode == 'text')
        self.seg_dur_widget.setVisible(mode == 'duration')
        self.seg_count_widget.setVisible(mode == 'count')

    def _on_select_skill(self):
        last = config.get('last_skill_path', '')
        default_dir = os.path.dirname(last) if last and os.path.isfile(last) else os.path.expanduser('~')
        path, _ = QFileDialog.getOpenFileName(
            self, '选择 SKILL 文件', default_dir,
            'Markdown 文件 (*.md);;所有文件 (*.*)'
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            self._skill_prompt = content
            self._skill_path   = path
            short = Path(path).name
            if len(short) > 24:
                short = short[:22] + '…'
            self.skill_label.setText(f"✅ {short}")
            self.skill_label.setStyleSheet(
                f"color: {Theme.SUCCESS_TEXT}; font-size: {Typography.SIZE_XS}px;"
            )
            config.set('last_skill_path', path)
        except Exception as e:
            QMessageBox.critical(self, '读取失败', f'无法读取 SKILL 文件：\n{e}')

    def _on_select_material(self):
        default_dir = self._material_folder or config.get('default_material_folder', '') or ''
        folder = QFileDialog.getExistingDirectory(self, '选择素材文件夹', default_dir)
        if folder:
            self._material_folder = folder
            self.material_label.setText(Path(folder).name)
            self.material_label.setStyleSheet(
                f"color: {Theme.SUCCESS_TEXT}; font-size: {Typography.SIZE_XS}px;"
            )
            config.set('default_material_folder', folder)

    def _on_select_bgm(self):
        default_dir = self._bgm_folder or config.get('default_bgm_folder', '') or ''
        folder = QFileDialog.getExistingDirectory(self, '选择 BGM 文件夹', default_dir)
        if folder:
            files = self._scan_bgm(folder)
            if not files:
                QMessageBox.warning(self, '提示', '所选文件夹中没有找到音频文件')
                return
            self._bgm_folder = folder
            self._bgm_files  = files
            self.bgm_label.setText(f"{Path(folder).name}  ({len(files)} 首)")
            self.bgm_label.setStyleSheet(
                f"color: {Theme.SUCCESS_TEXT}; font-size: {Typography.SIZE_XS}px;"
            )
            config.set('default_bgm_folder', folder)

    def _on_select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, '选择输出目录',
                                                   config.get('output_dir', './output/'))
        if folder:
            self.output_label.setText(folder)
            config.set('output_dir', folder)

    @staticmethod
    def _scan_bgm(folder: str) -> list:
        exts = {'.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg', '.wma'}
        files = []
        for f in Path(folder).rglob('*'):
            if f.suffix.lower() in exts:
                files.append(str(f))
        return files

    def _on_open_output(self):
        d = config.get('output_dir', './output/')
        path = str(Path(d).absolute())
        os.startfile(path)

    # ── MediaPush 派发 ──

    @staticmethod
    def _dispatch_state_path(inbox_dir: str) -> Path:
        return Path(inbox_dir) / '.dispatch_state.json'

    def _read_dispatch_counts(self, inbox_dir: str) -> dict:
        from datetime import date as _date, timedelta as _td
        import json as _json
        p = self._dispatch_state_path(inbox_dir)
        if not p.exists():
            return {}
        try:
            data = _json.loads(p.read_text(encoding='utf-8'))
            if isinstance(data.get('counts'), dict):
                return {str(k): int(v) for k, v in data['counts'].items()}
            if 'date' in data and 'batches_dispatched' in data:
                last_date = _date.fromisoformat(data['date'])
                tomorrow_of_then = (last_date + _td(days=1)).isoformat()
                n = int(data['batches_dispatched'])
                if n > 0:
                    return {tomorrow_of_then: min(n, self.SLOTS_PER_DAY)}
        except Exception:
            pass
        return {}

    def _write_dispatch_counts(self, inbox_dir: str, counts: dict) -> None:
        from datetime import datetime as _dt
        import json as _json
        p = self._dispatch_state_path(inbox_dir)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                'schema': 2,
                'updated_at': _dt.now().isoformat(timespec='seconds'),
                'counts': dict(sorted(counts.items())),
            }
            p.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    def _next_available_slot(self, counts: dict):
        from datetime import date as _date, datetime as _dt, time as _time, timedelta as _td
        SLOT_TIMES = [_time(7, 0), _time(12, 0), _time(18, 0)]
        earliest = _dt.now() + _td(hours=self.SLOT_LEAD_HOURS)
        cursor = _date.today()
        end = cursor + _td(days=365)
        while cursor < end:
            next_idx = counts.get(cursor.isoformat(), 0)
            for slot_idx in range(next_idx, self.SLOTS_PER_DAY):
                sched = _dt.combine(cursor, SLOT_TIMES[slot_idx])
                if sched >= earliest:
                    return cursor, slot_idx
            cursor += _td(days=1)
        raise RuntimeError('未来 365 天的发布槽位都已排满')

    def _maybe_dispatch_batch(self):
        from datetime import datetime, time as _time
        from core.mediapush_dispatcher import write_batch

        BATCH_SIZE = config.get('auto_dispatch_batch_size', 12)
        if not config.get('auto_dispatch_to_mediapush', True):
            return
        SLOT_TIMES = [_time(7, 0), _time(12, 0), _time(18, 0)]
        SLOT_NAMES = ['morning', 'noon', 'evening']
        inbox_dir = config.get(
            'mediapush_inbox_path',
            r'J:\MagicTool\emdia\MediaPush\inbox'
        )

        undispatched = [it for it in self._queue
                        if it.state == ST_DONE and not it.dispatched]
        if len(undispatched) < BATCH_SIZE:
            return

        counts = self._read_dispatch_counts(inbox_dir)

        while len(undispatched) >= BATCH_SIZE:
            batch_items = undispatched[:BATCH_SIZE]
            try:
                target_date, slot_idx = self._next_available_slot(counts)
            except RuntimeError as e:
                self._log(f'  ❌ {e}')
                return
            slot_name = SLOT_NAMES[slot_idx]
            slot_time = SLOT_TIMES[slot_idx]
            scheduled = datetime.combine(target_date, slot_time)

            video_paths = [it.output_paths[0] for it in batch_items if it.output_paths]
            if len(video_paths) < BATCH_SIZE:
                self._log(f'  ⚠ 派发批次视频不足 {BATCH_SIZE}（实际 {len(video_paths)}），跳过本次')
                return

            try:
                bdir = write_batch(inbox_dir, video_paths, scheduled, slot_name, move=True)
            except Exception as e:
                self._log(f'  ❌ 派发到 MediaPush 失败：{type(e).__name__}: {e}')
                return

            for it in batch_items:
                it.dispatched = True
                it.output_paths = []
            counts[target_date.isoformat()] = slot_idx + 1
            self._write_dispatch_counts(inbox_dir, counts)
            self._log(
                f'  📤 派发到 MediaPush：{len(video_paths)} 条 → '
                f'{scheduled.strftime("%m-%d %H:%M")}（{slot_name}，'
                f'{target_date.isoformat()} 当日已用 {slot_idx+1}/{self.SLOTS_PER_DAY}）'
            )
            undispatched = undispatched[BATCH_SIZE:]

    def _on_send_to_publish(self):
        import shutil
        import random

        done_paths = []
        for item in self._queue:
            if item.state == ST_DONE:
                for p in item.output_paths:
                    if Path(p).exists():
                        done_paths.append(Path(p))

        if not done_paths:
            QMessageBox.information(self, '无可发送的视频',
                                    '队列中没有已完成的视频，请先执行完成后再发送。')
            return

        to_publish_dir = Path(config.get('to_publish_dir', './to_publish/'))
        sub_folders = [
            to_publish_dir / '早上发布7点',
            to_publish_dir / '中午发布12点',
            to_publish_dir / '晚上发布17点',
        ]
        for f in sub_folders:
            f.mkdir(parents=True, exist_ok=True)

        random.shuffle(done_paths)
        n = len(sub_folders)
        groups = [done_paths[i::n] for i in range(n)]

        copied, skipped = 0, 0
        for folder, group in zip(sub_folders, groups):
            for src in group:
                dest = folder / src.name
                if dest.exists():
                    skipped += 1
                else:
                    try:
                        shutil.move(str(src), str(dest))
                        copied += 1
                        self._log(f'  ✅ {src.name}  →  {folder.name}')
                    except Exception as e:
                        self._log(f'  ❌ {src.name} 移动失败：{str(e)}')

        self._log(f'\n📤 发送完成：{copied} 个视频均分到 {n} 个文件夹')
        if skipped:
            self._log(f'   （{skipped} 个已跳过）')

        if copied > 0:
            reply = QMessageBox.question(
                self, '发送成功',
                f'已将 {copied} 个视频均分到 3 个待发布文件夹。\n\n是否打开目录查看？',
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                os.startfile(str(to_publish_dir.absolute()))

    # ── 执行控制 ──

    def _on_start(self):
        if not self._queue:
            QMessageBox.warning(self, '队列为空', '请先添加需要处理的脚本')
            return
        if not self._skill_prompt:
            QMessageBox.warning(self, '未设置 SKILL', '请先选择 SKILL 文件')
            return
        if not self._material_folder or not Path(self._material_folder).is_dir():
            QMessageBox.warning(self, '未设置素材', '请先选择素材文件夹')
            return
        if not config.get('script_llm_api_key', ''):
            QMessageBox.warning(self, '未配置 API Key',
                                '请先在「API 配置」页填写豆包大模型 API Key')
            return

        self._running = True
        self._paused  = False
        self._current_idx = 0
        self._current_llm_ver = 0

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.log_edit.clear()
        self._log('▶ 开始执行批量流程…')

        for item in self._queue:
            item.state = ST_PENDING
            item.error_msg = ''
            item.rewritten = ''
            item.audio_path = ''
            item.timestamps = []
            item.segments = []
            item.output_paths = []
            item.title = ''
            item.cover_text = ''
            item.cover_prompt = ''
            item.cover_image_path = ''
            item.cover_ready = False
            item._pending_compose_paths = []
            item.retry_count = 0
            item.dispatched = False
        for w in self._item_widgets:
            w.set_state(ST_PENDING)

        self._run_current()

    def _on_pause(self):
        if not self._running:
            return
        if self._paused:
            self._paused = False
            self.pause_btn.setText('⏸ 暂停')
            self._log('▶ 继续执行…')
            self._run_current()
        else:
            self._paused = True
            self.pause_btn.setText('▶ 继续')
            self._log('⏸ 已暂停，当前步骤执行完后将停下')

    def _on_stop(self):
        self._running = False
        self._paused  = False
        if self._llm_thread and self._llm_thread.isRunning():
            self._llm_thread.terminate()
        if self._cover_thread and self._cover_thread.isRunning():
            self._cover_thread.terminate()
        if self._tts_worker and self._tts_worker.isRunning():
            self._tts_worker.terminate()
        if self._compose_worker and self._compose_worker.isRunning():
            self._compose_worker.stop()
        self._log('⏹ 已终止')
        self._finish_session()

    def _finish_session(self):
        self._running = False
        self._paused  = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText('⏸ 暂停')
        self.stop_btn.setEnabled(False)
        self.review_frame.hide()

    def _run_current(self):
        if not self._running:
            return
        while (self._current_idx < len(self._queue) and
               self._queue[self._current_idx].state in (ST_DONE, ST_FAILED, ST_SKIPPED)):
            self._current_idx += 1

        if self._current_idx >= len(self._queue):
            done   = sum(1 for x in self._queue if x.state == ST_DONE)
            failed = sum(1 for x in self._queue if x.state == ST_FAILED)
            skip   = sum(1 for x in self._queue if x.state == ST_SKIPPED)
            self._log(f'\n🎉 全部执行完成！成功 {done} 条，失败 {failed} 条，跳过 {skip} 条')
            from core.tts import tts_stats
            self._log(f'📊 本次 TTS 字数：{tts_stats.session:,} 字　累计：{tts_stats.total:,} 字')
            self._finish_session()
            return

        if self._paused:
            return

        item = self._queue[self._current_idx]
        total_ver = self.llm_ver_spin.value()
        ver_str = f'（版本 {self._current_llm_ver + 1}/{total_ver}）' if total_ver > 1 else ''
        self._log(f'\n── 第 {self._current_idx + 1} 条{ver_str} ─────────────────')
        self._step_llm(item)

    # ── Step 1: LLM ──

    def _step_llm(self, item: ScriptItem):
        self._set_state(item, ST_LLM)
        self._log('① LLM 生成文案…')

        api_key = config.get('script_llm_api_key', '')
        model   = config.get('script_llm_model', 'doubao-seed-2.0-pro')

        self._llm_thread = LLMThread(
            api_key=api_key,
            model=model,
            skill_prompt=self._skill_prompt + JSON_SUFFIX,
            source_text=item.source_text,
            parent=self,
        )
        self._llm_thread.finished.connect(lambda text, i=item: self._on_llm_done(i, text))
        self._llm_thread.error.connect(lambda msg, i=item: self._on_llm_error(i, msg))
        self._llm_thread.start()

    def _on_select_cover_bg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择封面底图', str(Path(self._cover_bg_path).parent) if self._cover_bg_path else '',
            '图片文件 (*.png *.jpg *.jpeg);;所有文件 (*.*)'
        )
        if not path:
            return
        self._cover_bg_path = path
        self.cover_label.setText(Path(path).name)
        self.cover_label.setStyleSheet(
            f"color: {Theme.SUCCESS_TEXT}; font-size: {Typography.SIZE_XS}px;"
        )
        config.set('cover_bg_path', path)

    def _on_llm_done(self, item: ScriptItem, text: str):
        import json, re

        raw = text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'\s*```$', '', raw).strip()

        rewritten = ''
        title = ''
        cover_text = ''
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                rewritten  = (data.get('rewritten') or '').strip()
                title      = (data.get('title') or '').strip()
                cover_text = (data.get('cover_text') or '').strip()
        except Exception:
            try:
                json_match = re.search(r'\{[\s\S]*\}', raw)
                if json_match:
                    data = json.loads(json_match.group())
                    if isinstance(data, dict):
                        rewritten  = (data.get('rewritten') or '').strip()
                        title      = (data.get('title') or '').strip()
                        cover_text = (data.get('cover_text') or '').strip()
            except Exception:
                pass

        if not rewritten:
            rewritten = self._clean_script(text)

        rewritten = re.sub(r'\n{2,}', '\n', rewritten).strip()
        title = title[:20]
        if not title:
            first = re.split(r'[。！？\n]', rewritten)[0].strip()
            title = first[:20] if first else ''
        cover_text = cover_text[:4]
        if not cover_text:
            cover_text = (title or rewritten)[:3]

        item.rewritten = rewritten
        if self._current_llm_ver == 0:
            item.title = title
            item.cover_text = cover_text

        auto_save(rewritten, 'batch_rewrite')
        self._log(f'  ✅ LLM 完成（{len(rewritten)} 字，标题：{title or "（未获取）"}，封面：{cover_text or "（未获取）"}）')

        if self.review_check.isChecked():
            self._set_state(item, ST_REVIEW)
            self._log('  👁 等待审核…')
            self._show_review(item)
        else:
            self._step_tts(item)

    def _maybe_retry_or_fail(self, item: ScriptItem, stage: str) -> bool:
        if item.retry_count < MAX_GEN_RETRIES:
            item.retry_count += 1
            self._log(
                f'  ⟳ 自动重试 {item.retry_count}/{MAX_GEN_RETRIES}'
                f'（{stage} 失败：{item.source_text[:20]}...）'
            )
            item.rewritten = ''
            item.audio_path = ''
            item.timestamps = []
            item.segments = []
            item.output_paths = []
            item.title = ''
            item.cover_text = ''
            item.cover_prompt = ''
            item.cover_image_path = ''
            item.cover_ready = False
            item._pending_compose_paths = []
            self._current_llm_ver = 0
            self._set_state(item, ST_PENDING)
            if not self._paused:
                self._step_llm(item)
            return True
        self._set_state(item, ST_FAILED)
        self._next()
        return False

    def _on_llm_error(self, item: ScriptItem, msg: str):
        item.error_msg = msg
        self._log(f'  ❌ LLM 失败：{msg}')
        self._maybe_retry_or_fail(item, 'LLM')

    # ── 审核 ──

    def _show_review(self, item: ScriptItem):
        self.review_edit.setPlainText(item.rewritten)
        self.review_frame.show()
        self._reviewing_item = item

    def _on_review_continue(self):
        item = getattr(self, '_reviewing_item', None)
        if item is None:
            return
        item.rewritten = self.review_edit.toPlainText().strip()
        self.review_frame.hide()
        self._log('  ✅ 审核通过，继续执行…')
        self._step_tts(item)

    def _on_review_skip(self):
        item = getattr(self, '_reviewing_item', None)
        if item is None:
            return
        self.review_frame.hide()
        self._log('  ⏭ 跳过此条')
        self._set_state(item, ST_SKIPPED)
        self._next()

    # ── Step 2: TTS ──

    def _step_tts(self, item: ScriptItem):
        self._set_state(item, ST_TTS)
        self._log('② 生成音频…')

        speed = self.speed_spin.value() / 100.0
        volume = self.volume_spin.value()
        voice_id = self.voice_combo.currentData()
        if voice_id:
            config.set('tts_voice', voice_id)
        self._tts_worker = self.TTSWorker(item.rewritten, speed=speed, volume=volume)
        self._tts_worker.finished.connect(lambda p, ts, d, i=item: self._on_tts_done(i, p, ts, d))
        self._tts_worker.error.connect(lambda msg, i=item: self._on_tts_error(i, msg))
        self._tts_worker.progress.connect(lambda msg: self._log(f'  … {msg}'))
        self._tts_worker.start()

    def _on_tts_done(self, item: ScriptItem, audio_path: str, timestamps: list, duration: float):
        item.audio_path  = audio_path
        item.timestamps  = timestamps
        item.duration    = duration
        auto_save_audio(audio_path, item.rewritten)
        self._log(f'  ✅ 音频完成（{duration:.1f}s，{len(timestamps)} 字）')
        self._step_segment(item)

    def _on_tts_error(self, item: ScriptItem, msg: str):
        item.error_msg = msg
        self._log(f'  ❌ TTS 失败：{msg}')
        self._maybe_retry_or_fail(item, 'TTS')

    # ── Step 3: 分段 ──

    def _step_segment(self, item: ScriptItem):
        self._set_state(item, ST_SEGMENT)
        mode = self.seg_mode_combo.currentData()
        self._log(f'③ 分段（{self.seg_mode_combo.currentText()}）…')

        try:
            if mode == 'text':
                min_dur = self.min_dur_spin.value() / 10.0
                if not item.timestamps:
                    raise ValueError('按文案分段需要字级时间戳，但 TTS 未返回时间戳')
                segments = segment_by_text(
                    item.timestamps,
                    min_duration=min_dur,
                    audio_duration=item.duration,
                )
            elif mode == 'duration':
                seg_secs = float(self.seg_dur_spin.value())
                segments = self._make_duration_segments(item.duration, seg_secs)
            else:
                seg_count = self.seg_count_spin.value()
                segments = self._make_count_segments(item.duration, seg_count)

            if not segments:
                raise ValueError('分段结果为空')

            if mode != 'text':
                self._fill_segment_text(segments, item.rewritten)

            for seg in segments:
                seg['folder_path'] = self._material_folder
                seg['audio_path']  = item.audio_path

            item.segments = segments
            self._log(f'  ✅ 分段完成（{len(segments)} 段）')
            self._step_compose(item)
        except Exception as e:
            item.error_msg = str(e)
            self._log(f'  ❌ 分段失败：{e}')
            self._set_state(item, ST_FAILED)
            self._next()

    @staticmethod
    def _make_duration_segments(total_dur: float, seg_secs: float) -> list:
        segments = []
        start = 0.0
        while start < total_dur:
            end = min(start + seg_secs, total_dur)
            segments.append({'start': start, 'end': end, 'duration': end - start, 'text': ''})
            start = end
        return segments

    @staticmethod
    def _make_count_segments(total_dur: float, count: int) -> list:
        seg_dur = total_dur / count
        return [
            {'start': i * seg_dur, 'end': (i + 1) * seg_dur, 'duration': seg_dur, 'text': ''}
            for i in range(count)
        ]

    @staticmethod
    def _fill_segment_text(segments: list, full_text: str):
        n = len(segments)
        if n == 0 or not full_text:
            return
        chars = list(full_text.replace('\n', ' '))
        chunk = max(1, len(chars) // n)
        for i, seg in enumerate(segments):
            seg['text'] = ''.join(chars[i * chunk: (i + 1) * chunk])

    # ── Step 4: 合成 ──

    def _step_compose(self, item: ScriptItem):
        self._set_state(item, ST_COMPOSE)
        count      = self.count_spin.value()
        resolution = self.res_combo.currentText()
        fps        = config.get('output_fps', 30)
        bgm_vol    = self.bgm_vol_spin.value()
        output_dir = config.get('output_dir', './output/')
        self._log(f'④ 合成视频（×{count}，{resolution}）…')

        self._compose_worker = self.ComposeWorker(
            segments=item.segments,
            timestamps=item.timestamps,
            count=count,
            resolution=resolution,
            fps=fps,
            bgm_folder=self._bgm_folder or None,
            bgm_files=self._bgm_files,
            bgm_volume=bgm_vol,
            output_dir=output_dir,
        )
        self._compose_worker.progress.connect(
            lambda msg, cur, total: self._log(f'  … {msg}')
        )
        self._compose_worker.progress_detail.connect(
            lambda cur, total, fname, status: self._log(
                f'  {"✅" if status == "success" else "❌"} {fname}'
            )
        )
        self._compose_worker.finished.connect(
            lambda paths, i=item: self._on_compose_done(i, paths)
        )
        self._compose_worker.error.connect(
            lambda msg, i=item: self._on_compose_error(i, msg)
        )
        self._compose_worker.start()

    def _on_compose_done(self, item: ScriptItem, paths: list):
        item.output_paths.extend(paths)
        total_ver = self.llm_ver_spin.value()
        self._log(f'  ✅ 视频合成完成（{len(paths)} 个）')

        self._current_llm_ver += 1
        if self._current_llm_ver < total_ver:
            item.rewritten   = ''
            item.audio_path  = ''
            item.timestamps  = []
            item.segments    = []
            self._log(f'\n  → 开始生成版本 {self._current_llm_ver + 1}/{total_ver}…')
            self._set_state(item, ST_LLM)
            if self._paused:
                self._log('\n⏸ 暂停中，等待继续…')
                return
            self._step_llm(item)
        else:
            self._step_finalize(item, list(item.output_paths))

    def _on_compose_error(self, item: ScriptItem, msg: str):
        item.error_msg = msg
        total_ver = self.llm_ver_spin.value()
        self._log(f'  ❌ 合成失败（版本 {self._current_llm_ver + 1}/{total_ver}）：{msg}')
        self._current_llm_ver += 1
        if self._current_llm_ver < total_ver:
            item.rewritten  = ''
            item.audio_path = ''
            item.timestamps = []
            item.segments   = []
            self._log(f'  → 继续版本 {self._current_llm_ver + 1}/{total_ver}…')
            if not self._paused:
                self._step_llm(item)
        else:
            self._maybe_retry_or_fail(item, '合成')

    # ── 收尾 ──

    def _step_finalize(self, item: ScriptItem, paths: list):
        import re, shutil
        from core.video_composer import VideoComposer

        self._set_state(item, ST_RENAME)
        self._log('  🎬 插入封面 / 重命名…')

        raw_title = item.title or item.rewritten[:20]
        safe_title = re.sub(r'[\\/:*?"<>|\s，,]', '', raw_title)[:30].strip()

        def resolve_path(parent: Path, base: str, suffix: str) -> Path:
            candidate = parent / f"{base}{suffix}.mp4"
            if not candidate.exists():
                return candidate
            n = 2
            while True:
                candidate = parent / f"{base}{suffix}_{n}.mp4"
                if not candidate.exists():
                    return candidate
                n += 1

        vc = VideoComposer()
        final_paths = []
        for i, src in enumerate(paths):
            src_path = Path(src)
            if not src_path.exists():
                final_paths.append(src)
                continue

            suffix = f'_{i+1}' if len(paths) > 1 else ''
            new_path = resolve_path(src_path.parent, safe_title, suffix)
            new_name = new_path.name

            ok = False
            if self._cover_bg_path and Path(self._cover_bg_path).exists():
                cover_display_text = item.cover_text or item.title[:4] or ''
                ok = vc.prepend_cover_image(
                    video_path=src,
                    title=cover_display_text,
                    output_path=str(new_path),
                    cover_bg_path=self._cover_bg_path,
                )
            if ok:
                try:
                    src_path.unlink()
                except Exception:
                    pass
                final_paths.append(str(new_path))
                self._log(f'    ✅ {new_name}')
            else:
                shutil.move(str(src_path), str(new_path))
                final_paths.append(str(new_path))
                self._log(f'    ⚠️ 封面插入失败，已重命名：{new_name}')

        item.output_paths = final_paths
        self._set_state(item, ST_DONE)
        self._log(f'  🎉 完成！共 {len(final_paths)} 个文件')
        try:
            self._maybe_dispatch_batch()
        except Exception as e:
            self._log(f'  ⚠ 派发到 MediaPush 失败：{type(e).__name__}: {e}')
        self._next()

    # ── 推进 ──

    def _next(self):
        if not self._running:
            return
        self._current_idx += 1
        self._current_llm_ver = 0
        if self._paused:
            self._log('\n⏸ 暂停中，等待继续…')
            return
        self._run_current()

    # ── 工具 ──

    def _set_state(self, item: ScriptItem, state: str):
        item.state = state
        try:
            idx = self._queue.index(item)
            total_ver = self.llm_ver_spin.value()
            extra = ''
            if total_ver > 1 and state not in (ST_DONE, ST_FAILED, ST_SKIPPED, ST_PENDING):
                extra = f'{STATE_LABEL[state]} v{self._current_llm_ver + 1}/{total_ver}'
            self._item_widgets[idx].set_state(state, extra)
        except (ValueError, IndexError):
            pass

    def _log(self, msg: str):
        self.log_edit.append(msg)
        if self.log_edit.document().blockCount() > 1000:
            cursor = self.log_edit.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def _restore_defaults(self):
        last = config.get('last_skill_path', '')
        if last and os.path.isfile(last):
            try:
                with open(last, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                self._skill_prompt = content
                self._skill_path   = last
                short = Path(last).name
                if len(short) > 24:
                    short = short[:22] + '…'
                self.skill_label.setText(f"✅ {short}")
                self.skill_label.setStyleSheet(
                    f"color: {Theme.SUCCESS_TEXT}; font-size: {Typography.SIZE_XS}px;"
                )
            except Exception:
                pass

    # ── 样式辅助 ──

    @staticmethod
    def _make_panel(title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {Theme.BG_SURFACE};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Spacing.BORDER_RADIUS_MD}px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        if title:
            t = QLabel(title)
            t.setStyleSheet(
                f"font-size: {Typography.SIZE_SM}px; "
                f"font-weight: {Typography.WEIGHT_MEDIUM}; "
                f"color: {Theme.TEXT_SECONDARY}; "
                f"border: none; background: transparent;"
            )
            layout.addWidget(t)
        return frame

    def _small_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setStyleSheet(self._secondary_btn_style())
        return btn

    def _primary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {Theme.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
                font-size: {Typography.SIZE_BASE}px;
                font-weight: {Typography.WEIGHT_MEDIUM};
                padding: 0 14px;
            }}
            QPushButton:hover {{ background: {Theme.ACCENT_HOVER}; }}
            QPushButton:disabled {{ background: {Theme.BG_ELEVATED}; color: {Theme.TEXT_TERTIARY}; }}
        """

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
                font-size: {Typography.SIZE_SM}px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                border-color: {Theme.ACCENT_PRIMARY};
                color: {Theme.ACCENT_PRIMARY};
            }}
            QPushButton:disabled {{ color: {Theme.TEXT_TERTIARY}; }}
        """

    def _spin_style(self) -> str:
        return f"""
            QSpinBox {{
                background: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
                font-size: {Typography.SIZE_XS}px;
                padding: 2px 4px;
            }}
        """

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: {Spacing.BORDER_RADIUS_SM}px;
                font-size: {Typography.SIZE_SM}px;
                padding: 3px 8px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {Theme.BG_SURFACE};
                color: {Theme.TEXT_PRIMARY};
                selection-background-color: {Theme.SIDEBAR_ITEM_ACTIVE};
            }}
        """


# ── 简易输入对话框 ──
class _InputDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('手动添加脚本')

        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        self._dlg = QDialog(parent)
        self._dlg.setWindowTitle('手动添加脚本')
        self._dlg.resize(480, 220)

        layout = QVBoxLayout(self._dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl = QLabel("粘贴原始文案（一条）：")
        lbl.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-size: {Typography.SIZE_SM}px;")
        layout.addWidget(lbl)

        self._edit = QTextEdit()
        self._edit.setStyleSheet(f"""
            QTextEdit {{
                background: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_LIGHT};
                border-radius: 4px;
                font-size: {Typography.SIZE_SM}px;
                padding: 6px;
            }}
        """)
        layout.addWidget(self._edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._dlg.accept)
        btns.rejected.connect(self._dlg.reject)
        layout.addWidget(btns)

    def exec_(self):
        return self._dlg.exec_()

    def get_text(self) -> str:
        return self._edit.toPlainText().strip()
