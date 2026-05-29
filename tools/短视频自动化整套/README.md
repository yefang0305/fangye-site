# 短视频自动化工具集

端到端短视频自动化工具集，覆盖**对标账号采集 → 文案提取 → 脚本库管理 → 批量生产调度 → 发布分发**全链路。

## 目录

- [架构概览](#架构概览)
- [功能模块](#功能模块)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [使用示例](#使用示例)
- [集成 MediaPush](#集成-mediapush)
- [项目结构](#项目结构)
- [依赖说明](#依赖说明)
- [常见问题](#常见问题)

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                    对标账号采集 (benchmark_ingestion)          │
│                                                              │
│  Markdown链接源  ──→  链接路由识别  ──→  账号主页展开           │
│       │                    │                │                │
│       ▼                    ▼                ▼                │
│  单视频链接           账号主页链接       作品列表链接            │
│       │                    │                │                │
│       └────────────────────┴────────────────┘                │
│                           │                                  │
│                           ▼                                  │
│                    视频下载 (yt-dlp + CR TubeGet)             │
│                           │                                  │
│                           ▼                                  │
│                    ASR 语音转文字                              │
│               (faster-whisper 本地 / 外部脚本)                 │
│                           │                                  │
│                           ▼                                  │
│                    文本清洗 (规则 + LLM)                       │
│                           │                                  │
│                           ▼                                  │
│                    适配审查 (LLM 人设过滤)                     │
│                    keep / rewrite / reject                    │
│                           │                                  │
│                           ▼                                  │
│                    脚本库存储 (JSON 索引 + TXT 文件)           │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              批量生产调度 (auto_batch_from_txt)                │
│                                                              │
│  脚本库 TXT  ──→  批量导入  ──→  VideoCut 批量自动化处理       │
│                          ──→  视频生成                        │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│             发布分发 (mediapush_dispatcher)                    │
│                                                              │
│  生成视频  ──→  写入 inbox 批次目录  ──→  MediaPush 自动拾取    │
│                          ──→  多平台发布                      │
└──────────────────────────────────────────────────────────────┘
```

## 功能模块

### 1. 链接路由 (`link_router`)

自动识别视频平台链接类型：
- **抖音**: 短链接、单视频、账号主页、合集
- **B站**: 单视频、合集、账号空间
- **YouTube**: 单视频、播放列表、频道
- **小红书**: 笔记、账号主页
- **快手**: 单视频、账号主页

### 2. 账号主页展开 (`douyin_profile`)

输入抖音账号主页链接，自动分页拉取该账号的全部作品链接。支持设置页大小和最大翻页数。

### 3. 视频下载 (`downloader`)

- **主下载器**: yt-dlp，支持多平台
- **抖音专用**: CR TubeGet 直链解析，解决 yt-dlp Cookie 过期问题
- 自动回退：yt-dlp 失败时自动切换到 CR TubeGet

### 4. ASR 语音转文字

- **本地模式** (`local_asr_engine`): 使用 faster-whisper + CUDA 加速
- **外部模式** (`external_asr_engine`): 调用独立 ASR 项目的 batch_asr.py 脚本
- 支持 large-v3 模型，中文优化

### 5. 文本清洗

- **规则清洗** (`rule_cleaner`): 修复常见 ASR 同音字错误、去除口癖词、添加标点、分段落、过滤带货内容
- **LLM 清洗** (`llm_cleaner`): 使用豆包/OpenAI 兼容 API 进行语义级校对

### 6. 适配审查 (`adaptation_reviewer`)

基于 LLM 的内容适配审查，按固定人设（男道士/男命理师）过滤：
- 时效错位检测
- 身份错位检测（女性视角、博主口吻）
- 作者自述/过往经历识别
- 不可迁移内容标记

三种决策：`keep`（通过）、`rewrite`（改写后通过）、`reject`（拒绝）

### 7. 脚本库 (`script_library`)

- JSON 索引文件存储元数据（URL、状态、时间戳）
- 清洗后的脚本以独立 TXT 文件存储
- 支持状态追踪：ready → used

### 8. 状态追踪 (`state_store`)

- 持久化 JSON 文件记录每个 URL 的处理状态
- 支持断点续跑、自动跳过已处理链接
- 失败计数和永久失败标记

### 9. 发布分发 (`mediapush_dispatcher`)

- 将生成的视频打包为批次目录
- 写入 `manifest.json` 供 MediaPush 的 `InboxWatcher` 自动拾取
- 支持按时段（早/中/晚）命名批次

## 环境要求

- **Python**: 3.10+
- **操作系统**: Windows（推荐）/ Linux / macOS
- **GPU**: 推荐 NVIDIA GPU（CUDA）用于本地 ASR
- **CR TubeGet**: 仅抖音下载需要（[cr-soft.top](http://www.cr-soft.top)）
- **FFmpeg**: 视频音频提取（ASR 预处理）
- **yt-dlp**: 多平台视频下载

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone <repo-url>
cd 短视频自动化整套

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API Key、CR TubeGet 路径等
```

### 3. 运行测试

```bash
python -m pytest tests/ -v
```

### 4. 运行采集流水线

```python
from automation_suite.benchmark_ingestion.orchestrator import BenchmarkAgentOrchestrator
from automation_suite.benchmark_ingestion.douyin_profile import DouyinProfileExpander
from automation_suite.benchmark_ingestion.downloader import YtDlpVideoDownloader
from automation_suite.benchmark_ingestion.local_asr_engine import LocalWhisperASREngine
from automation_suite.benchmark_ingestion.script_library import ScriptLibrary
from automation_suite.benchmark_ingestion.state_store import IngestionStateStore

# 初始化组件
profile_expander = DouyinProfileExpander(
    crtubeget_dir="J:/MagicTool/crtubeget",
    cookie_file="douyin_cookies.txt"
)
downloader = YtDlpVideoDownloader(crtubeget_dir="J:/MagicTool/crtubeget")
asr_engine = LocalWhisperASREngine(model_name="large-v3", device="cuda")
script_library = ScriptLibrary("./data/library.json")
state_store = IngestionStateStore("./data/ingestion_state.json")

# 创建编排器
orchestrator = BenchmarkAgentOrchestrator(
    profile_expander=profile_expander,
    downloader=downloader,
    asr_engine=asr_engine,
    llm_client=None,  # 可选
    adaptation_reviewer=None,  # 可选
    script_library=script_library,
    video_library_dir="./data/videos",
    state_store=state_store,
)

# 采集对标账号的前 10 个视频
result = orchestrator.run_profile(
    "https://www.douyin.com/user/MS4wLjABAAAA...",
    limit=10
)
print(f"完成: {result['completed']}, 拒绝: {result['rejected']}")
```

## 配置说明

详细配置见 `.env.example`。关键配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API 密钥（豆包/OpenAI 兼容） | 无 |
| `LLM_MODEL` | LLM 模型名称 | `doubao-seed-2.0-pro` |
| `CRTUBEGET_DIR` | CR TubeGet 安装目录 | 无 |
| `ASR_MODEL` | Whisper 模型 | `large-v3` |
| `ASR_DEVICE` | 推理设备 | `cuda` |
| `MEDIAPUSH_INBOX_DIR` | MediaPush inbox 目录 | 无 |

## 使用示例

`examples/` 目录包含合成示例文件，可安全提交：

### 输入示例 (`examples/input/`)

- `benchmark_links.md` — 对标视频链接 Markdown 文件格式
- `douyin_profile_response.json` — 抖音账号接口响应结构

### 输出示例 (`examples/output/`)

- `library.json` — 脚本库索引文件格式
- `ingestion_state.json` — 摄入状态文件格式
- `manifest.json` — MediaPush 批次清单格式

## 集成 MediaPush

本工具集通过 `mediapush_dispatcher.py` 与 [MediaPush](../../emdia/MediaPush) 集成：

1. **VideoCut** 批量生成视频后，视频文件存放在输出目录
2. **mediapush_dispatcher.write_batch()** 将视频打包为批次目录写入 MediaPush 的 `inbox/`
3. **MediaPush 的 InboxWatcher** 自动检测新批次，解析 `manifest.json`
4. 按 `scheduled_time` 在指定时间发布到抖音/快手/小红书

```python
from automation_suite.mediapush_dispatcher import write_batch
from datetime import datetime, timedelta

write_batch(
    inbox_dir="J:/MagicTool/emdia/MediaPush/inbox",
    video_paths=["output/video1.mp4", "output/video2.mp4"],
    scheduled_time=datetime.now() + timedelta(hours=1),
    slot_name="morning",
)
```

## 项目结构

```
短视频自动化整套/
├── automation_suite/                  # 核心包
│   ├── __init__.py
│   ├── mediapush_dispatcher.py        # MediaPush 批次分发
│   └── benchmark_ingestion/           # 对标采集子包
│       ├── __init__.py
│       ├── models.py                  # 数据模型
│       ├── orchestrator.py            # 顶层编排器
│       ├── pipeline.py                # 采集流水线
│       ├── downloader.py              # 视频下载 (yt-dlp + CR TubeGet)
│       ├── douyin_cr.py              # 抖音直链解析
│       ├── douyin_profile.py          # 抖音主页展开
│       ├── local_asr_engine.py        # 本地 Whisper ASR
│       ├── external_asr_engine.py     # 外部 ASR 脚本调用
│       ├── rule_cleaner.py            # 规则文本清洗
│       ├── llm_cleaner.py             # LLM 文本清洗
│       ├── adaptation_reviewer.py     # 适配审查 (人设过滤)
│       ├── link_router.py             # 链接类型识别
│       ├── md_source.py               # Markdown 链接源处理
│       ├── script_library.py          # 脚本库管理
│       └── state_store.py             # 状态持久化
├── tests/                             # 测试
│   ├── test_benchmark_ingestion_core.py
│   ├── test_benchmark_ingestion_pipeline.py
│   └── test_benchmark_ingestion_orchestrator.py
├── examples/                          # 示例文件
│   ├── input/
│   └── output/
├── docs/                              # 文档
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## 依赖说明

### 必需依赖

| 包 | 用途 |
|----|------|
| `yt-dlp` | 多平台视频下载 |
| `faster-whisper` | 本地语音识别 (ASR) |
| `requests` | HTTP 请求（API 调用、视频直链下载） |

### 可选依赖

| 包/工具 | 用途 | 备注 |
|---------|------|------|
| CR TubeGet | 抖音直链解析和 Cookie 导出 | Windows 工具，需单独安装 |
| FFmpeg | 视频音频提取 | ASR 预处理必需 |
| CUDA Toolkit | GPU 加速 ASR | 非必需，CPU 也可运行 |

### 哪些部分需要本地模型/API Key/Cookie/CR TubeGet

| 功能 | 依赖项 |
|------|--------|
| 抖音视频下载 | CR TubeGet 或 抖音 Cookie |
| 本地 ASR | faster-whisper 模型（首次自动下载） |
| LLM 文案清洗 | 火山引擎/OpenAI API Key |
| 适配审查 | 火山引擎/OpenAI API Key |
| MediaPush 分发 | MediaPush 项目 + 各平台账号登录 |

## 常见问题

### Q: 抖音 Cookie 过期怎么办？

使用 CR TubeGet 的 `crck.exe` 自动导出新鲜 Cookie，或在浏览器中手动导出 douyin.com 的 Netscape 格式 `cookies.txt`。

### Q: ASR 速度太慢？

- 使用 CUDA GPU（推荐 NVIDIA RTX 系列）
- 尝试较小的模型（如 `medium`）
- 使用 `int8_float16` 计算类型

### Q: 适配审查太严格？

审查规则是保守策略，默认宁可多拒绝。可以通过调整 `REVIEW_SYSTEM_PROMPT` 或修改人设描述来放宽条件。

### Q: 如何添加新平台支持？

在 `link_router.py` 的 `RULES` 列表中添加 URL 匹配规则，在 `md_source.py` 的 `_looks_like_video_url` 中添加域名。

## 许可证

MIT
