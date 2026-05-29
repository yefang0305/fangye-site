"""
main_desktop.py - 抖音批量视频生成工具 桌面工作台入口
──────────────────────────────────────────────────
PyQt5 桌面应用，提供批量自动化视频生成工作台。

使用方式：
  python main_desktop.py                # 启动桌面 GUI
  python main.py tts --text "..."       # CLI 模式（独立入口）
"""

import sys
import os
import threading
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QStatusBar,
    QMessageBox,
)

from core.config import config, get_app_dir
from core.tts import TTSGenerator, TTSAuthError, TTSNetworkError, TTSParamError
from core.video_composer import VideoComposer
from ui.theme import Theme, Typography, Spacing, build_qss
from ui.batch_automation.batch_automation_page import BatchAutomationPage


# ──────────────────────────────────────────────────────────────
#  Worker classes (defined here to avoid circular imports)
# ──────────────────────────────────────────────────────────────

class TTSWorker(QThread):
    """TTS 语音合成工作线程"""
    finished = pyqtSignal(str, list, float)   # audio_path, timestamps, duration
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int, str)

    def __init__(self, text, speed=None, volume=100):
        super().__init__()
        self.text = text
        self.speed = speed
        self.volume = volume

    def run(self):
        try:
            self.progress.emit("正在生成音频...")
            self.progress_percent.emit(0, "正在连接语音合成服务...")
            tts = TTSGenerator()

            def progress_callback(percent, message):
                self.progress_percent.emit(percent, message)
                self.progress.emit(message)

            audio_path, timestamps = tts.generate(
                self.text, speed=self.speed, volume=self.volume,
                progress_callback=progress_callback
            )
            duration = tts.get_audio_duration(audio_path)
            self.finished.emit(audio_path, timestamps, duration)
        except TTSAuthError as e:
            self.error.emit(str(e))
        except TTSNetworkError as e:
            self.error.emit(str(e))
        except TTSParamError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))


class ComposeWorker(QThread):
    """视频合成工作线程"""
    finished = pyqtSignal(list)       # output_paths
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int, int)   # message, current, total
    step_progress = pyqtSignal(str)
    progress_detail = pyqtSignal(int, int, str, str)  # cur, total, filename, status

    def __init__(self, segments, timestamps, count, resolution, fps,
                 bgm_folder, bgm_files, bgm_volume, output_dir):
        super().__init__()
        self.segments = segments
        self.timestamps = timestamps
        self.count = count
        self.resolution = resolution
        self.fps = fps
        self.bgm_folder = bgm_folder
        self.bgm_files = bgm_files
        self.bgm_volume = bgm_volume
        self.output_dir = output_dir
        self._should_stop = False

        self._pause_event = threading.Event()
        self._pause_event.set()

    def stop(self):
        self._should_stop = True
        self._pause_event.set()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def run(self):
        import random
        try:
            composer = VideoComposer()
            output_paths = []

            for i in range(self.count):
                if self._should_stop:
                    break
                self._pause_event.wait()
                if self._should_stop:
                    break

                video_filename = f"output_{i+1:03d}.mp4"
                self.progress.emit(f"正在生成第 {i+1} / {self.count} 个视频...", i+1, self.count)
                self.step_progress.emit(f"处理分段 1/{len(self.segments)}…")

                try:
                    bgm_path = None
                    if self.bgm_files:
                        bgm_path = random.choice(self.bgm_files)

                    output_path = composer.compose(
                        self.segments,
                        timestamps=self.timestamps,
                        resolution=self.resolution,
                        fps=self.fps,
                        bgm_path=bgm_path,
                        bgm_volume=self.bgm_volume,
                        output_dir=self.output_dir,
                        index=i+1
                    )
                    output_paths.append(output_path)
                    self.progress_detail.emit(i+1, self.count, video_filename, "success")
                except Exception as e:
                    self.progress_detail.emit(i+1, self.count, video_filename, "failed")

            self.finished.emit(output_paths)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────────────────────
#  Main Desktop Window
# ──────────────────────────────────────────────────────────────

class DesktopWorkbench(QMainWindow):
    """批量视频生成桌面工作台"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("抖音批量视频生成 - 桌面工作台")
        self.resize(1200, 750)
        self.setMinimumSize(900, 550)

        # 应用主题样式
        self.setStyleSheet(build_qss())

        # 中心控件：批量自动化工作台
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.batch_page = BatchAutomationPage(
            tts_worker_class=TTSWorker,
            compose_worker_class=ComposeWorker,
            parent=self,
        )
        layout.addWidget(self.batch_page)

        self.setCentralWidget(central)

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            f"background: {Theme.BG_BASE}; color: {Theme.TEXT_TERTIARY}; "
            f"border-top: 1px solid {Theme.BORDER_LIGHT};"
        )
        self.status_bar.showMessage("就绪 - 请先选择 SKILL 文件并添加脚本")
        self.setStatusBar(self.status_bar)

        # 检查 FFmpeg 和 TTS 配置
        self._check_environment()

    def _check_environment(self):
        """检查运行环境"""
        import subprocess

        # 检查 FFmpeg
        ffmpeg_dir = get_app_dir() / "ffmpeg"
        ffmpeg_path = ffmpeg_dir / "ffmpeg.exe"
        if ffmpeg_path.exists():
            self.status_bar.showMessage("FFmpeg ✓ | 就绪")
        else:
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True)
                self.status_bar.showMessage("FFmpeg (系统) ✓ | 就绪")
            except FileNotFoundError:
                self.status_bar.showMessage("⚠ FFmpeg 未找到，视频合成将不可用")

    def closeEvent(self, event):
        """关闭窗口时保存配置"""
        try:
            config._save_config()
        except Exception:
            pass
        event.accept()


# ──────────────────────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────────────────────

def main():
    """启动桌面工作台"""
    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("抖音批量视频生成")
    app.setOrganizationName("VideoTool")

    window = DesktopWorkbench()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
