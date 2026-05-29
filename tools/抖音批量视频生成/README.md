# 抖音批量视频生成工具

> 一键将文案转成带字幕、BGM、随机素材混剪的抖音短视频，支持批量自动化生成。

## 产品价值

解决短视频创作者的核心痛点：**文案 → 成片** 的全自动流水线。

- 🎙️ **TTS 语音合成**：接入火山引擎 TTS，将文案转为自然语音，同时获取字级时间戳
- 🤖 **LLM 文案重写**：通过豆包大模型 + SKILL 文件，对原始文案进行风格化重写
- ✂️ **智能分段**：基于标点和时长自动将文案拆分为适合视频切换的片段
- 🎬 **素材随机匹配**：每个分段从指定文件夹随机选取视频素材裁剪拼接
- 🎵 **BGM 混音**：自动循环背景音乐，支持音量调节
- 📝 **字幕生成**：基于 TTS 时间戳生成 ASS 字幕（支持字体、颜色、描边配置）
- 🖼️ **封面生成**：Pillow 渲染标题封面并拼接到视频开头
- 🔄 **批量任务队列**：JSON 配置驱动，一次配置，批量生成多条视频
- 🖥️ **桌面工作台**：PyQt5 图形界面，拖拽导入、三栏布局、可视化进度
- 📤 **MediaPush 集成**：自动按时间槽派发到发布队列

## 两种运行模式

本项目提供两种使用方式：

| 模式 | 入口文件 | 说明 |
|------|----------|------|
| 🖥️ **桌面工作台** | `main_desktop.py` | PyQt5 图形界面，批量自动化工作台，支持拖拽导入、可视化进度 |
| ⌨️ **CLI 引擎** | `main.py` | 命令行工具，适合脚本集成和自动化流水线 |

### 桌面工作台（推荐）

```bash
python main_desktop.py
```

打开后可以看到：
- **左栏**：脚本队列，支持拖拽 TXT/JSON 文件导入，手动添加文案
- **中栏**：全局参数，SKILL 文件、TTS 音色/语速、分段模式、素材文件夹、BGM、输出设置
- **右栏**：执行日志 + 审核区 + 控制按钮

### CLI 引擎

```bash
# TTS 合成
python main.py tts --text "你的文案" --output ./output

# 视频合成
python main.py compose --segments segments.json --audio ./audio.mp3

# 批量任务
python main.py batch --tasks tasks.json
```

## 系统架构

```
抖音批量视频生成/
├── main.py                    # 命令行入口（CLI 引擎）
├── main_desktop.py            # 桌面工作台入口（PyQt5 GUI）
├── core/
│   ├── config.py              # 配置管理（JSON 持久化）
│   ├── tts.py                 # TTS 语音合成（火山引擎 WebSocket）
│   ├── text_segmenter.py      # 基于时间戳的文案分段
│   ├── ai_segment.py          # AI 智能分段（豆包大模型）
│   ├── subtitle.py            # ASS 字幕生成
│   ├── video_composer.py      # 视频合成引擎（FFmpeg）
│   ├── task_queue.py          # 任务队列数据模型
│   ├── auto_saver.py          # 文案/音频自动保存
│   └── mediapush_dispatcher.py # MediaPush 派发器
├── ui/
│   ├── __init__.py
│   ├── theme.py               # UI 主题系统（深色主题）
│   ├── voice_selector_dialog.py # 音色选择对话框
│   └── batch_automation/
│       ├── __init__.py
│       └── batch_automation_page.py  # 批量自动化工作台页面
├── requirements.txt           # Python 依赖
├── README.md                  # 项目说明（本文件）
└── docs/
    └── extraction-notes.md    # 提取说明
```

### 核心流程

```
文案 → [LLM重写] → 新文案 + 标题 + 封面文字
         ↓
    [TTS合成] → 音频 + 字级时间戳
         ↓
    [文案分段] → 分段列表（每段绑定素材文件夹）
         ↓
    [素材匹配] → 每个分段随机选取素材裁剪
         ↓
    [视频拼接] → 分段视频拼接 + 转场
         ↓
    [BGM混音] → 口播 + 背景音乐混合
         ↓
    [字幕烧录] → ASS 字幕叠加
         ↓
    [封面插入] → 标题封面 + 视频拼接
         ↓
      成品视频
```

## 环境要求

- **Python**: 3.10+
- **FFmpeg**: 必须安装并在 PATH 中可用（或将 ffmpeg.exe 放在 `ffmpeg/` 目录下）
- **操作系统**: Windows / macOS / Linux
- **桌面模式额外依赖**: PyQt5（见 requirements.txt）

## 安装

```bash
# 1. 克隆项目
git clone <repo-url>
cd 抖音批量视频生成

# 2. 创建虚拟环境（推荐使用 uv）
uv venv
# 或
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. 安装依赖
uv pip install -r requirements.txt
# 或
pip install -r requirements.txt
```

### FFmpeg 安装

- **Windows**: 下载 [FFmpeg](https://ffmpeg.org/download.html)，将 `ffmpeg.exe` 和 `ffprobe.exe` 放到项目 `ffmpeg/` 目录
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

## 使用方式

### 桌面工作台（推荐新手使用）

```bash
# 启动图形界面
python main_desktop.py
```

工作台使用步骤：
1. 选择 **SKILL 文件**（LLM 重写的风格提示词，.md 格式）
2. 选择 **素材文件夹**（包含视频素材）
3. 可选：选择 BGM 文件夹、设置音色/语速/分段参数
4. **导入脚本**：拖拽 TXT/JSON 文件到左栏，或手动粘贴文案
5. 点击 **▶ 开始执行**，等待流水线自动完成
6. 输出视频在 `output/` 目录下

### CLI 引擎（适合脚本集成）

#### 1. 配置 API 密钥

```bash
python main.py config --set-key volcengine_app_id --set-value "你的AppID"
python main.py config --set-key volcengine_token --set-value "你的AccessToken"
```

配置文件存储在 `config/settings.json`。

#### 2. TTS 语音合成

```bash
python main.py tts --text "今天给大家分享一个超级实用的技巧..."
python main.py tts --file script.txt --speed 1.0 --output ./output
python main.py tts --text "..." --voice "zh_female_zhimeng_uranus_bigtts" --volume 120
```

#### 3. 文案分段

```bash
python main.py segment --timestamps-file ./output/timestamps.json --output ./output
```

#### 4. 视频合成

```bash
python main.py compose --segments segments.json --bgm ./bgm/music.mp3 --bgm-volume 30
```

#### 5. 批量任务

```bash
python main.py batch --tasks tasks.json
```

## API 配置

### 火山引擎 TTS（必需）

1. 注册 [火山引擎](https://www.volcengine.com/) 账号
2. 开通语音合成服务（TTS）
3. 获取 AppID 和 Access Token
4. 通过 `config` 命令或直接编辑 `config/settings.json` 配置

### 豆包大模型（桌面工作台 LLM 重写必需）

桌面工作台的 LLM 文案重写功能需要豆包大模型 API Key：

```bash
python main.py config --set-key script_llm_api_key --set-value "你的API Key"
python main.py config --set-key script_llm_model --set-value "doubao-seed-2.0-pro"
```

## 字幕配置

支持以下字幕样式配置项（在 `config/settings.json` 中设置）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `subtitle_font` | Microsoft YaHei | 字体名称 |
| `subtitle_font_size` | 52 | 字号 |
| `subtitle_color` | &H00FFFFFF | 文字颜色（ABGR） |
| `subtitle_outline` | true | 是否描边 |
| `subtitle_outline_color` | &H00000000 | 描边颜色 |
| `subtitle_outline_size` | 2 | 描边粗细 |
| `subtitle_shadow` | true | 是否阴影 |
| `subtitle_position_y` | 80 | 字幕垂直位置（百分比，底部=100） |

## 打包说明

本项目可配合 PyInstaller 打包为独立 EXE：

```bash
# CLI 版本
pyinstaller --onefile --name 抖音批量视频生成 main.py

# 桌面版本
pyinstaller --onefile --name 抖音批量视频生成桌面版 main_desktop.py
```

注意：打包后需将 `ffmpeg/` 目录和 `config/` 目录放在 EXE 同目录下。

## 已知限制

1. **FFmpeg 依赖**：视频处理完全依赖 FFmpeg，必须单独安装
2. **TTS 服务**：仅支持火山引擎 TTS（WebSocket 协议），需要联网
3. **字体依赖**：封面生成使用 Windows 系统字体，macOS/Linux 需手动指定
4. **桌面模式**：需要 PyQt5，Linux 下可能需要额外安装 Qt 库
5. **字幕字体**：ASS 字幕字体需要系统中已安装对应字体
6. **视频编码**：默认使用 H.264/AAC 编码，输出 MP4 格式
7. **素材要求**：支持常见视频格式（mp4, mov, avi, mkv, wmv, flv, webm）

## 许可

本项目从 [VideoCut](https://github.com/) 桌面工具提取核心视频生成管线，仅供学习和个人使用。
