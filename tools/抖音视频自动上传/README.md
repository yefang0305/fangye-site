# MediaPush — 抖音视频自动上传工作台

多账号抖音视频批量发布桌面工具。支持账号管理、收件箱自动监听、定时/立即发布队列、作品清理、私信管理。

## 核心价值

- **批量发布**：一次将多个视频分配到不同账号组，定时或立即发布到抖音创作者后台
- **收件箱自动化**：VideoCut 视频剪辑工具输出到 `inbox/` 目录后，MediaPush 自动发现新批次、随机分配账号、入队发布
- **账号矩阵管理**：支持多平台（抖音/小红书/快手）账号的添加、扫码登录、登录态刷新、分组管理
- **发布记录与重试**：完整的任务日志、失败自动重试（无头→有头）、人工核验后补发
- **作品清理**：自动扫描低播放/低点赞作品，标记限流作品（有"查看详情"提示），一键清理
- **私信管理**：定时轮询陌生人私信、桌面通知提醒、手动回复、标记已处理

## 系统要求

- **Python** >= 3.11
- **操作系统**：Windows（Playwright Chromium 自动化）
- **依赖**：PyQt5（桌面 UI）、Playwright（浏览器自动化）、python-dotenv（环境配置）
- **浏览器**：Playwright 安装的 Chromium（`playwright install chromium`）

## 快速开始

### 1. 克隆/下载项目

```bash
cd 抖音视频自动上传
```

### 2. 创建虚拟环境并安装依赖

```bash
# 使用 uv（推荐）
uv venv
uv pip install -e .

# 或使用 pip
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### 3. 安装 Playwright 浏览器

```bash
playwright install chromium
```

### 4. 配置环境变量

```bash
copy .env.example .env
# 编辑 .env 文件，设置数据库路径、Profile 目录等
```

### 5. 启动

```bash
python main.py
```

## 账号与 Profile 设置

### 扫码添加账号

1. 在"账号管理"Tab 中，先创建一个组（如"国学号"）
2. 点击"添加账号(扫码)"，选择平台（抖音/小红书/快手）
3. 程序会弹出 Chromium 浏览器窗口，打开平台登录页
4. 用手机扫码登录
5. 登录成功后浏览器自动关闭，账号信息（含登录态 Cookie）保存在 `profiles/{account_id}/` 目录

### Profile 目录说明

- 每个账号对应 `profiles/{account_id}/` 子目录
- 目录内是完整的 Chromium 用户数据（Cookie、LocalStorage 等）
- **不要手动修改或删除**，否则登录态丢失
- **不要提交到 Git**（已在 `.gitignore` 中排除）

### 刷新登录状态

点击"刷新登录状态"按钮，程序会用无头浏览器访问每个账号的创作者后台，检测是否仍处于登录状态，并更新 UI 显示。

## 工作流程

### 方式一：手动发布

1. 在"发布任务"Tab 中选择视频文件夹（含 `.mp4` 文件）
2. 选择发布模式：立即发布 或 定时发布（需 ≥2 小时提前量）
3. 勾选目标发布组
4. 点击"开始发布"

### 方式二：收件箱自动发布（与 VideoCut 联动）

VideoCut 将视频批次输出到 `MEDIAPUSH_INBOX_PATH` 目录，格式为：

```
inbox/20260427-070000-morning/
  manifest.json     # {scheduled_time, videos: ["v1.mp4", "v2.mp4", ...]}
  v1.mp4
  v2.mp4
```

MediaPush 的后台 InboxWatcher 每 `MEDIAPUSH_INBOX_POLL_SECONDS` 秒扫描一次：
1. 发现新批次 → 解析 manifest
2. 随机分配活跃账号组 → 配对视频
3. 提交到发布队列 → 移动批次到 `processed/`
4. 写入 `result.json` 记录配对关系

### 发布队列机制

- 严格串行处理：同一时间只有一个 Chromium 实例运行
- 首次尝试使用**无头浏览器**（静默后台运行）
- 失败后自动重试一次，使用**有头浏览器**（用户可手动解决验证码）
- 有头重试仍失败 → 标记为 `failed`，用户可手动重试
- 支持立即发布和定时发布两种模式

### 发布记录

- "发布记录"Tab 展示所有任务的完整历史
- 支持重试失败的/卡住的/核验后缺失的任务
- 双击任意记录可打开对应账号的创作者后台（有头浏览器），方便人工核对
- 可删除历史记录（仅删数据库记录，不删视频文件）

### 作品清理

- "作品清理"Tab 扫描抖音作品管理页
- 自动标记：
  - 限流作品（有"查看详情"提示）
  - 发布超过 24 小时且播放 < 1000、点赞 < 30 的作品
- 点击"清理"按钮逐个删除
- 失败记录可单独重试

### 私信管理

- 每 1 小时自动轮询所有抖音账号的陌生人私信
- 桌面通知提醒新消息
- 右键菜单支持：打开私信后台、回复、标记已处理
- 回复时打开聊天窗口，实时刷新对话历史
- 消息数据持久化到 `data/message_cache.json`

## 运行测试

```bash
# 运行纯逻辑模块测试（不需要浏览器）
pytest tests/test_store.py tests/test_queue.py tests/test_inbox_watcher.py -q

# 运行所有纯逻辑测试
pytest tests/ -q --ignore=tests/test_douyin_cleanup.py --ignore=tests/test_douyin_message.py
```

浏览器相关测试（`test_douyin_cleanup.py`、`test_douyin_message.py`）需要真实的浏览器环境，默认跳过。

## 风险与限制

### 平台自动化风险

- **账号安全**：使用 Playwright 操控真实浏览器，行为模式接近人工操作，但仍有被平台检测的风险
- **验证码/二次验证**：首次发布用无头模式，失败后自动切有头模式让用户手动处理验证码
- **DOM 变更**：抖音创作者后台的 HTML 结构可能随时变化，需要更新 `publisher/douyin.py` 中的选择器常量
- **定时发布时间要求**：抖音要求定时发布时间 ≥ 当前时间 + 2 小时

### 已知问题

- 抖音发布页面有时会弹出"自主声明"弹窗，程序已自动处理"无需添加自主声明"选项
- 发布后抖音可能回到作品列表并显示上传任务窗口，程序会等待该窗口完成后才关闭浏览器
- 小红书和快手的发布功能暂未实现（仅支持账号管理和登录态检测）

### 验证建议

- 发布后建议到抖音创作者后台"作品管理"页核对
- 在"发布记录"Tab 中双击记录可快速打开对应账号的后台
- 定期检查 `logs/` 目录中的失败截图

## 与 VideoCut 的关系

MediaPush 最初作为 VideoCut 视频剪辑工具的下游发布模块开发：

- **VideoCut** 负责：脚本生成、视频剪辑、封面提取、视频渲染
- **MediaPush** 负责：账号管理、发布调度、平台自动化

VideoCut 通过 `inbox/` 目录与 MediaPush 解耦通信：
1. VideoCut 渲染完视频后，将批次写入 `MEDIAPUSH_INBOX_PATH`
2. MediaPush 的 InboxWatcher 自动发现并发布
3. 发布结果记录在 `processed/{batch_id}/result.json`

MediaPush 也可作为独立工具使用，不依赖 VideoCut。

## 项目结构

```
├── main.py                      # 入口：初始化 Store/Queue/Watcher/UI
├── pyproject.toml               # 项目依赖配置
├── .env.example                 # 环境变量模板
├── .gitignore
├── README.md
├── account/
│   ├── __init__.py
│   └── manager.py               # 账号管理：扫码添加、删除、登录刷新
├── db/
│   ├── __init__.py
│   └── store.py                 # SQLite 数据访问层
├── publisher/
│   ├── __init__.py
│   ├── base.py                  # Publisher 抽象基类
│   ├── queue.py                 # 发布任务队列（QThread）
│   ├── douyin.py                # 抖音发布器
│   ├── xiaohongshu.py           # 小红书发布器（登录/检测，发布未实现）
│   ├── kuaishou.py              # 快手发布器（登录/检测，发布未实现）
│   ├── inbox_watcher.py         # 收件箱监听器（VideoCut→MediaPush 桥接）
│   ├── douyin_message.py        # 抖音私信读取器
│   ├── message_reader.py        # 私信读取器抽象基类
│   ├── message_store.py         # 私信持久化存储
│   ├── message_scheduler.py     # 私信定时轮询调度器
│   ├── cover_extractor.py       # 视频首帧封面提取
│   └── douyin_cleanup.py        # 抖音作品清理工具
├── mediapush_ui/
│   ├── __init__.py
│   ├── main_window.py           # 主窗口（Tab 容器）
│   ├── mediapush_page.py        # 可嵌入 VideoCut 的独立页面
│   ├── account_panel.py         # 账号管理面板
│   ├── publish_panel.py         # 发布任务面板
│   ├── history_panel.py         # 发布记录面板
│   ├── cleanup_panel.py         # 作品清理面板
│   ├── message_panel.py         # 私信管理面板
│   ├── reply_dialog.py          # 私信回复对话框
│   └── browser_launcher.py      # 独立 Chromium 启动器
├── tests/
│   ├── test_store.py
│   ├── test_queue.py
│   ├── test_inbox_watcher.py
│   ├── test_message_store.py
│   ├── test_message_scheduler.py
│   ├── test_cover_extractor.py
│   ├── test_douyin_cleanup.py
│   ├── test_douyin_message.py
│   ├── test_douyin_publish_result.py
│   └── test_title_cleanup.py
└── docs/
    └── selectors_message.md     # 抖音私信页 DOM 选择器文档
```

## 技术栈

- **UI**：PyQt5
- **浏览器自动化**：Playwright (Chromium)
- **数据库**：SQLite
- **视频处理**：imageio-ffmpeg（封面提取）
- **环境配置**：python-dotenv
