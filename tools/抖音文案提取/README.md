# 抖音文案提取工具

基于本地 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 模型的视频口播文案提取工具，无需联网、无需 API Key。

## 功能

- 支持单个视频文件或批量目录导入
- 自动用 FFmpeg 提取音频并归一化（16kHz 单声道 WAV）
- 本地 faster-whisper 转录，支持中英文及自动检测
- 输出 `.txt`（纯文本）、`.md`（带时间戳）、`.json`（完整结构化数据）
- 内置口播文本清洗规则（去语气词、纠正常见 ASR 误识、加标点分段）

## 环境要求

- **Python**: 3.10+
- **FFmpeg**: 必须安装并在 PATH 中可用
  - Windows: 下载 [ffmpeg.exe](https://ffmpeg.org/download.html) 并添加到 PATH，或放入本目录
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg` / `dnf install ffmpeg`
- **GPU（可选）**: CUDA 兼容显卡 + cuBLAS/cuDNN，可大幅加速推理
- **磁盘**: 模型文件首次运行自动下载，`large-v3` 约 3 GB

## 快速开始

```bash
# 1. 创建虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行（首次会自动下载模型）
python cli.py /path/to/video.mp4
python cli.py /path/to/video_folder
```

## 命令行参数

```
python cli.py [输入路径] [选项]

位置参数:
  input                 视频文件路径或包含视频的目录（默认: 当前目录）

选项:
  -m, --model           faster-whisper 模型名称 (默认: large-v3)
                        可选: tiny, base, small, medium, large-v2, large-v3
  -d, --device          推理设备 (默认: cuda)
                        可选: cuda, cpu
  -c, --compute-type    计算精度 (默认: int8_float16)
                        可选: float16, int8_float16, int8
  -l, --language        语言代码 (默认: zh)
                        可选: zh, en, auto (自动检测)
  --model-dir           模型缓存目录 (默认: ~/.douyin_asr/models)
  -o, --output-dir      输出目录 (默认: ./output)
  --no-clean            跳过文本清洗，保留原始 ASR 输出
  --ext                 按扩展名过滤视频文件，逗号分隔 (例如: .mp4,.mov)
```

## 环境变量

所有参数也可以通过环境变量配置，命令行参数优先级更高：

| 变量                      | 对应参数       | 默认值              |
|---------------------------|---------------|--------------------|
| `DOUYIN_ASR_MODEL`        | `--model`     | `large-v3`         |
| `DOUYIN_ASR_DEVICE`       | `--device`    | `cuda`             |
| `DOUYIN_ASR_COMPUTE_TYPE` | `--compute-type` | `int8_float16`  |
| `DOUYIN_ASR_LANGUAGE`     | `--language`  | `zh`               |
| `DOUYIN_ASR_MODEL_DIR`    | `--model-dir` | `~/.douyin_asr/models` |
| `DOUYIN_ASR_OUTPUT_DIR`   | `--output-dir` | `./output`        |

## 模型选择建议

| 模型        | 大小   | 显存需求 | 速度   | 准确度 | 推荐场景         |
|------------|--------|---------|--------|--------|------------------|
| `tiny`     | ~150MB | 低      | 极快   | 低     | 快速测试         |
| `base`     | ~300MB | 低      | 快     | 一般   | 资源受限         |
| `small`    | ~1GB   | 中      | 中等   | 较好   | 日常使用         |
| `medium`   | ~3GB   | 高      | 较慢   | 好     | 追求质量         |
| `large-v3` | ~3GB   | 高      | 慢     | 最好   | 生产环境（推荐） |

## CPU 运行

如果没有 NVIDIA GPU，使用 CPU 推理：

```bash
python cli.py video.mp4 -d cpu -c int8
```

CPU 推理速度约为 GPU 的 1/5 ~ 1/10，建议使用 `small` 或 `medium` 模型。

## 输出示例

```
output/
├── 视频标题.txt      # 清洗后的纯文本
├── 视频标题.md       # 带元数据和分段时间戳的 Markdown
└── 视频标题.json     # 完整结构化数据（含原始文本、分段、时长等）
```

## 项目结构

```
抖音文案提取/
├── cli.py           # CLI 入口
├── asr_engine.py    # faster-whisper ASR 引擎
├── rule_cleaner.py  # 口播文本清洗规则
├── config.py        # 参数解析、文件发现、输出写入
├── requirements.txt # Python 依赖
├── test_local.py    # 非推理测试脚本
└── README.md        # 本文件
```
