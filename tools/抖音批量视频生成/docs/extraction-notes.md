# 提取说明

## 来源

本项目从 `J:\MagicTool\Standalone\VideoCut\video_tool` 桌面工具提取而来。

原始项目是一个基于 PyQt5 的全功能视频编辑桌面应用，包含 GUI 界面、视频编辑器、素材管理、
对标采集、文案提取、图片生成等多个子系统。

## 已提取的模块

| 模块 | 源文件 | 说明 |
|------|--------|------|
| `core/config.py` | `core/config.py` | 配置管理，移除 PyQt5 依赖和部分非核心配置项 |
| `core/tts.py` | `core/tts.py` | TTS 语音合成，保留完整 WebSocket 协议实现 |
| `core/text_segmenter.py` | `core/text_segmenter.py` | 文案分段，保留完整分句和合并逻辑 |
| `core/ai_segment.py` | `core/ai_segment.py` | AI 分段，保留豆包大模型接口 |
| `core/subtitle.py` | `core/subtitle.py` | ASS 字幕生成，保留完整样式和时间戳处理 |
| `core/video_composer.py` | `core/video_composer.py` | 视频合成引擎，保留核心 FFmpeg 管线 |
| `core/task_queue.py` | `core/task_queue.py` | 任务队列数据模型 |
| `main.py` | `main.py`（新建） | 命令行入口，整合上述模块 |

## 已排除的模块

以下模块属于原始桌面应用的功能，不在提取范围内：

| 模块 | 原因 |
|------|------|
| `ui/` 全部（main_window, task_queue_widget, segment_editor_widget 等） | PyQt5 GUI 界面，非本次提取目标 |
| `core/auto_saver.py` | 项目自动保存，GUI 功能 |
| `core/license.py` | 激活码管理，授权相关 |
| `core/manual_segmenter.py` | 手动分段编辑器，GUI 功能 |
| `core/benchmark_ingestion/` | 对标采集子系统，独立的另一套流程 |
| `core/mediapush_dispatcher.py` | 媒体分发推送 |
| `core/asr.py` | 语音识别（ASR），文案提取功能 |
| `standalone_editor.py` | 独立视频编辑器，另一个入口 |
| `manage.py` | 项目管理工具 |
| `auto/` | 自动发布模块 |
| `image create/` | 图片生成子系统 |
| `文案提取工具/` | 文案提取工具，独立的子项目 |
| `tests/` | 测试文件，与提取后的模块不匹配 |
| `workflow/` | 工作流配置和运行时输出 |
| `deps/` | 打包依赖（six, typing_extensions 等），应通过 pip 安装 |
| `hooks/` | PyInstaller 打包钩子 |
| `*.spec` | PyInstaller 打包配置 |
| `*.bat` | 打包/启动脚本 |

## 运行时目录（已排除）

| 目录 | 原因 |
|------|------|
| `venv/` | Python 虚拟环境 |
| `ffmpeg/` | 二进制工具（约 200MB） |
| `bin/` | 二进制文件 |
| `models/` | AI 模型文件（Whisper 等） |
| `output/` | 生成的视频输出 |
| `temp/` | 临时文件 |
| `logs/` | 日志文件 |
| `config/` | 配置文件（含密钥） |

## 适配变更

相对于原始代码，提取后的模块做了以下适配：

1. **移除 PyQt5 依赖**：删除 `from PyQt5.QtCore import QObject, pyqtSignal` 等 GUI 导入
2. **统一路径处理**：所有 `get_app_dir()` 调用统一指向项目根目录
3. **移除 Windows 子进程窗口隐藏**：简化 `SUBPROCESS_KWARGS` 配置（保留但不强制）
4. **精简配置项**：移除图片生成、ASR、对标采集等子系统的配置项
5. **添加命令行接口**：新建 `main.py` 提供 CLI 入口
6. **内部导入适配**：所有模块使用相对导入 `from .xxx import yyy`
