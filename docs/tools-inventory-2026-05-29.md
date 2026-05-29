# 工具盘点报告 — fangye.cc 本地工具清单

> **盘点日期**: 2026-05-29
> **盘点范围**: `J:\MagicTool\个人网站\tools\`
> **网站定位**: Astro 静态个人网站（AI 工具实验室 + 个人文章库 + 小工具展示）
> **盘点方法**: 只读扫描每个工具目录，读取 README、入口文件、依赖配置，分类评估网站接入方式

---

## 一、整体分类摘要

| 分类 | 数量 | 工具列表 |
|------|------|----------|
| **可直接站内运行 (yes)** | 2 | 公众号排版工具, MINIMAX语音生成 |
| **可部分提取 (partial)** | 1 | 抖音文案提取（清洗规则可提取） |
| **仅适合展示 (no-showcase)** | 5 | 抖音批量视频生成, 抖音视频下载, 抖音视频自动上传, 抖音主页链接采集, 桌面悬浮笔记 |
| **不建议公开展示 (no-private)** | 3 | 短视频自动化整套, 抖音私信同步(空), 公众号自动上传skill(空) |
| **已排除（辅助/生成目录）** | 1 | _拆分盘点（仅含 Codex 委托产物和旧盘点报告） |

---

## 二、逐工具详细分析

---

### 1. 公众号排版工具

- **本地路径**: `tools/公众号排版工具/`
- **当前入口**: `启动.bat` → `server.py` (Python HTTP 服务器) → `index.html` (浏览器)
- **工具类型**: Web 工具（纯前端 + 本地 API 代理）
- **主要功能**: 将文章内容通过 AI（豆包大模型）自动分析结构并套用专业排版风格，生成可直接粘贴进微信公众号编辑器的富文本内容
- **关键依赖**:
  - Python 3（仅用于本地 HTTP 服务器和 API 代理）
  - 豆包 API Key（用户自备，浏览器端输入，localStorage 存储）
  - Tailwind CSS CDN（前端样式）
- **输入**: 纯文本 / Markdown 文章内容
- **输出**: 富文本 HTML（可直接粘贴到公众号编辑器）
- **是否可站内运行**: **yes**
- **推荐接入方式**:
  - 核心逻辑全部在前端 `index.html` 中（原生 JS + Tailwind CSS）
  - `server.py` 仅用于 API 代理（解决浏览器 CORS），可以在 Astro 中直接调用豆包 API 或使用客户端 fetch
  - 建议新建 `src/pages/tools/wechat-formatter.astro`，将排版 UI 和逻辑内嵌
  - 排版主题（4 套）可以直接保留
- **风险或注意事项**:
  - 需要豆包 API Key，用户自备，不写入网站源码
  - 前端调用第三方 API 需注意 CORS，可考虑 Astro 服务端代理或保持纯客户端模式
  - 现有 PRD 文档完整，实现路径清晰
- **需要补充的信息**:
  - index.html 中 JS 逻辑的具体结构（文件较大，未完全读取）
  - 是否已有 API Key 默认值或测试配置

---

### 2. MINIMAX语音生成

- **本地路径**: `tools/MINIMAX语音生成/`
- **当前入口**: `subtitle-generator.html`
- **工具类型**: 纯前端 HTML 工具
- **主要功能**: 使用 MiniMax TTS API 将文本转为语音，生成带字幕的音频文件（支持语速、音调、音量调节）
- **关键依赖**:
  - MiniMax API Key（用户自备）
  - 纯浏览器端运行，无后端依赖
- **输入**: 文本内容
- **输出**: 带字幕时间戳的音频
- **是否可站内运行**: **yes**
- **推荐接入方式**:
  - 整个工具就是一个 HTML 文件，可直接改造为 Astro 页面
  - 新建 `src/pages/tools/minimax-tts.astro`
  - 将 CSS 适配为网站深色主题
  - API Key 由用户浏览器端输入，使用 localStorage 存储
- **风险或注意事项**:
  - 依赖 MiniMax API Key，需要用户自备
  - API 调用在浏览器端完成，需确认 MiniMax API 是否支持浏览器 CORS
  - 当前深色主题与网站风格基本兼容，适配成本低
- **需要补充的信息**:
  - MiniMax API 是否支持浏览器端直接调用（CORS 策略）
  - 工具生成的音频格式和下载方式

---

### 3. 抖音文案提取

- **本地路径**: `tools/抖音文案提取/`
- **当前入口**: `cli.py`（命令行工具）
- **工具类型**: Python CLI 工具
- **主要功能**: 基于本地 faster-whisper 模型提取视频口播文案，支持中英文转录，输出 TXT/MD/JSON 格式，内置口播文本清洗规则
- **关键依赖**:
  - Python 3.10+
  - FFmpeg（音频提取）
  - faster-whisper（本地 ASR 模型，~3GB）
  - CUDA GPU（可选，加速推理）
- **输入**: 视频文件（mp4/mov 等）或视频目录
- **输出**: 清洗后的文案（.txt / .md / .json）
- **是否可站内运行**: **partial**
- **推荐接入方式**:
  - **核心引擎**（faster-whisper + FFmpeg）无法在浏览器运行，不适合站内使用
  - **文本清洗规则**（`rule_cleaner.py`）可以提取为纯前端 JS 工具：
    - 去语气词（"嗯"、"啊"、"那个"）
    - 纠正常见 ASR 同音字误识
    - 添加标点、分段
    - 过滤带货内容
  - 建议新建 `src/pages/tools/text-polish.astro`，做一个"口播文案后处理"工具
- **风险或注意事项**:
  - 清洗规则是 Python 代码，需要翻译为 JavaScript
  - 规则依赖中文正则和字典，翻译需仔细测试
- **需要补充的信息**:
  - `rule_cleaner.py` 中具体规则列表和字典规模
  - 是否需要保留原始转录功能入口（仅本地使用）

---

### 4. 抖音视频下载

- **本地路径**: `tools/抖音视频下载/`
- **当前入口**: `app.py` → Flask Web 服务器 → 浏览器 `http://127.0.0.1:5080`
- **工具类型**: Python Web 工具（Flask + yt-dlp + CR TubeGet）
- **主要功能**: 从抖音作品链接批量下载视频，支持 yt-dlp 和 CR TubeGet 双路线
- **关键依赖**:
  - Python 3
  - Flask（Web 服务）
  - yt-dlp（视频下载）
  - CR TubeGet 运行时（`qjs.exe`, `crck.exe`, DLL 等，仅 Windows）
  - 抖音 Cookie（登录态，可选但建议）
- **输入**: 抖音视频链接列表（每行一个）
- **输出**: 下载的视频文件 + 下载报告（Markdown/JSON）
- **是否可站内运行**: **no-showcase**
- **推荐接入方式**:
  - 不适合 Astro 静态网站站内运行（需要 Python 后端 + yt-dlp + Windows 专用运行时）
  - 适合做成项目展示卡片：说明功能、运行方式、依赖，指向本地路径
  - `status: 'showcase'`，`href` 指向 `/tools/` 或新建详情页
- **风险或注意事项**:
  - 涉及平台内容下载，存在版权和平台合规风险
  - 依赖抖音 Cookie，可能触发风控
  - CR TubeGet 运行时包含第三方 DLL/EXE，仅 Windows 可用
  - 不应在公开网站上提供直接下载功能
- **需要补充的信息**: 无

---

### 5. 抖音主页链接采集

- **本地路径**: `tools/抖音主页链接采集/`
- **当前入口**: `app.py` → Flask Web 服务器 → 浏览器 `http://127.0.0.1:5999`
- **工具类型**: Python Web 工具（Flask + requests）
- **主要功能**: 从抖音个人主页链接批量提取所有公开作品的视频链接，导出为 Markdown
- **关键依赖**:
  - Python 3.9+
  - Flask
  - requests（调用抖音 API）
  - 可选抖音 Cookie（登录态）
- **输入**: 抖音个人主页 URL
- **输出**: Markdown 文件（编号列表 + 时间戳）
- **是否可站内运行**: **no-showcase**
- **推荐接入方式**:
  - 不适合 Astro 静态网站站内运行（需要 Python 后端 + 调用抖音 API）
  - 适合做成项目展示卡片
  - `status: 'showcase'`
- **风险或注意事项**:
  - 直接调用抖音 API，可能触发风控
  - 抖音 API 可能变更导致工具失效
  - Cookie 敏感信息不应出现在公开网站
- **需要补充的信息**: 无

---

### 6. 抖音批量视频生成

- **本地路径**: `tools/抖音批量视频生成/`
- **当前入口**: `main_desktop.py`（PyQt5 桌面工作台）/ `main.py`（CLI 引擎）
- **工具类型**: Python 桌面应用 + CLI
- **主要功能**: 文案 → 成片全自动流水线：TTS 语音合成 → LLM 文案重写 → 智能分段 → 素材混剪 → BGM 混音 → 字幕生成 → 封面生成 → 批量任务队列
- **关键依赖**:
  - Python 3.10+
  - FFmpeg（视频处理核心）
  - PyQt5（桌面 UI）
  - 火山引擎 TTS（WebSocket，需 API Key）
  - 豆包大模型（LLM 重写，需 API Key）
  - pydub, Pillow, websockets, openai, requests
- **输入**: 文案文本（TXT/JSON）、素材视频文件夹、BGM 文件夹
- **输出**: 成品 MP4 视频（含字幕、BGM、封面）
- **是否可站内运行**: **no-showcase**
- **推荐接入方式**:
  - 完全不适合 Astro 静态网站（需要 Python + FFmpeg + PyQt5 + GPU + 多个 API Key）
  - 适合做成项目展示卡片，展示架构图和核心流程
  - `status: 'showcase'`
- **风险或注意事项**:
  - 依赖多个商业 API（火山引擎、豆包），需要付费
  - FFmpeg 需要单独安装
  - 桌面模式依赖 PyQt5
  - 字幕字体依赖系统字体
- **需要补充的信息**: 无

---

### 7. 抖音视频自动上传 (MediaPush)

- **本地路径**: `tools/抖音视频自动上传/`
- **当前入口**: `main.py` → PyQt5 桌面应用
- **工具类型**: Python 桌面应用（PyQt5 + Playwright）
- **主要功能**: 多账号抖音视频批量发布桌面工具，支持账号管理、收件箱自动监听、定时/立即发布队列、作品清理、私信管理
- **关键依赖**:
  - Python 3.11+
  - PyQt5（桌面 UI）
  - Playwright + Chromium（浏览器自动化）
  - SQLite（数据持久化）
  - python-dotenv（环境配置）
- **输入**: 视频文件（.mp4）+ 发布配置
- **输出**: 发布结果（数据库记录 + 日志）
- **是否可站内运行**: **no-showcase**
- **推荐接入方式**:
  - 完全不适合 Astro 静态网站
  - 涉及浏览器自动化操控抖音创作者后台，平台风险高
  - 适合做成项目展示卡片（不展示具体自动化细节）
  - `status: 'showcase'`
- **风险或注意事项**:
  - 使用 Playwright 操控真实浏览器登录抖音创作者后台
  - 账号 Cookie 和 Profile 数据敏感，不可公开
  - 有账号安全风险（被平台检测自动化）
  - `.env` 文件包含敏感路径配置
  - 小红书和快手发布功能未实现
- **需要补充的信息**: 无

---

### 8. 短视频自动化整套

- **本地路径**: `tools/短视频自动化整套/`
- **当前入口**: 通过 Python API 调用（`BenchmarkAgentOrchestrator`）
- **工具类型**: Python 工具集（无独立入口，需编程调用）
- **主要功能**: 端到端短视频自动化工具集：对标账号采集 → 文案提取 → 脚本库管理 → 批量生产调度 → 发布分发
- **关键依赖**:
  - yt-dlp（视频下载）
  - faster-whisper（本地 ASR）
  - CR TubeGet（抖音直链解析，仅 Windows）
  - FFmpeg
  - 火山引擎/OpenAI API Key（LLM 清洗和审查）
  - CUDA GPU（推荐，用于 ASR 加速）
- **输入**: 对标账号链接、视频链接
- **输出**: 脚本库（JSON + TXT）、MediaPush 批次清单
- **是否可站内运行**: **no-private**
- **推荐接入方式**:
  - 不适合公开展示任何内容
  - 涉及平台采集、批量下载、自动化发布全链路
  - 包含对标账号采集（竞争分析）和适配审查（人设过滤）等高风险功能
  - 如需展示，仅做内部记录
- **风险或注意事项**:
  - 涉及多个平台的采集和自动化操作（抖音、B站、YouTube、小红书、快手）
  - 包含 LLM 驱动的"适配审查"功能（自动判断内容是否适合搬运/改写）
  - 与 MediaPush 集成，形成完整的内容搬运→改写→发布流水线
  - `.env.example` 可能暴露配置结构
  - 合规风险极高
- **需要补充的信息**: 无

---

### 9. 桌面悬浮笔记

- **本地路径**: `tools/桌面悬浮笔记/悬浮笔记/`
- **当前入口**: `npm start` → Electron 桌面应用
- **工具类型**: Electron 桌面应用
- **主要功能**: Windows 桌面悬浮快捷文本管理与复制工具，像素风格悬浮图标，毛玻璃展开面板，分组管理常用话术/提示词/密钥
- **关键依赖**:
  - Node.js
  - Electron v35+
  - electron-builder（打包）
- **输入**: 用户手动输入（文本片段）
- **输出**: 本地 JSON 文件（数据持久化）
- **是否可站内运行**: **no-showcase**
- **推荐接入方式**:
  - 不适合 Astro 静态网站（Electron 桌面应用）
  - 适合做成项目展示卡片，展示截图和功能说明
  - `status: 'showcase'`
  - 可以提供打包后的绿色版 EXE 下载链接（如果用户愿意公开）
- **风险或注意事项**:
  - Electron 应用 + `node_modules` 体积很大（不适合提交到网站仓库）
  - 用户数据存储在本地 `userData` 目录
  - 可以作为独立开源项目展示
- **需要补充的信息**:
  - 是否有打包好的 EXE 可供下载
  - 是否有截图可展示

---

### 10. 抖音私信同步

- **本地路径**: `tools/抖音私信同步/`
- **当前入口**: 目录为空（无任何文件）
- **工具类型**: 未开发 / 已移除
- **主要功能**: 未知（推测为抖音私信同步相关）
- **关键依赖**: 无
- **输入**: 无
- **输出**: 无
- **是否可站内运行**: **no-private**
- **推荐接入方式**: 不列入网站工具列表（空目录）
- **风险或注意事项**: 空目录，跳过
- **需要补充的信息**: 确认是否为已废弃项目，是否需要保留目录

---

### 11. 公众号自动上传skill

- **本地路径**: `tools/公众号自动上传skill/`
- **当前入口**: 目录为空（无任何文件）
- **工具类型**: 未开发 / 已移除
- **主要功能**: 未知（推测为公众号文章自动上传相关 skill）
- **关键依赖**: 无
- **输入**: 无
- **输出**: 无
- **是否可站内运行**: **no-private**
- **推荐接入方式**: 不列入网站工具列表（空目录）
- **风险或注意事项**: 空目录，跳过
- **需要补充的信息**: 确认是否为已废弃项目，是否需要保留目录

---

### 已排除目录

| 目录 | 排除原因 |
|------|----------|
| `_拆分盘点/` | 仅含 Codex 委托产物（`.codex/` 目录下的 claude_delegate 产物）和旧盘点报告 `工具拆分盘点报告.md`，属于工作流辅助目录，非工具本身 |

---

## 三、建议 `src/data/tools.ts` 新增条目

以下是基于盘点结果建议新增的条目草稿。不直接修改 `src/data/tools.ts`，待用户确认后再操作。

```ts
// ── 可站内运行 (usable) ──

{
  name: '公众号排版助手',
  slug: 'wechat-formatter',
  description: '将文章内容通过 AI 自动分析结构并套用专业排版风格，生成可直接粘贴进微信公众号编辑器的富文本内容。',
  category: '文本处理',
  status: 'usable',
  href: '/tools/wechat-formatter/',
  featured: true,
},
{
  name: 'MiniMax TTS 字幕',
  slug: 'minimax-tts',
  description: '使用 MiniMax TTS API 将文本转为语音并生成带时间戳的字幕，支持语速和音调调节。',
  category: '语音工具',
  status: 'usable',
  href: '/tools/minimax-tts/',
  featured: false,
},

// ── 可部分提取 (usable，仅清洗规则) ──

{
  name: '口播文案后处理',
  slug: 'text-polish',
  description: '清理 ASR 转录文本中的语气词、纠正常见误识、自动添加标点和分段，适合处理视频口播文案。',
  category: '文本处理',
  status: 'usable',
  href: '/tools/text-polish/',
  featured: false,
},

// ── 仅展示 (showcase) ──

{
  name: '抖音视频下载工具',
  slug: 'douyin-downloader',
  description: '基于 yt-dlp 和 CR TubeGet 的抖音视频批量下载工具，支持多路线下载和 Cookie 管理。本地 Python Web 工具。',
  category: '视频工具',
  status: 'showcase',
  href: '/tools/',
  featured: false,
},
{
  name: '抖音主页链接采集',
  slug: 'douyin-profile-linker',
  description: '从抖音个人主页批量提取公开作品链接，导出为 Markdown 文件。本地 Python Web 工具。',
  category: '数据采集',
  status: 'showcase',
  href: '/tools/',
  featured: false,
},
{
  name: '抖音批量视频生成',
  slug: 'douyin-batch-video',
  description: '文案→成片全自动流水线：TTS 合成、智能分段、素材混剪、字幕生成、封面渲染。Python 桌面工作台 + CLI。',
  category: '视频工具',
  status: 'showcase',
  href: '/tools/',
  featured: true,
},
{
  name: 'MediaPush 发布工作台',
  slug: 'mediapush',
  description: '多账号抖音视频批量发布桌面工具，支持账号管理、定时发布、作品清理和私信管理。PyQt5 + Playwright。',
  category: '发布工具',
  status: 'showcase',
  href: '/tools/',
  featured: false,
},
{
  name: '桌面悬浮笔记',
  slug: 'floating-snippets',
  description: 'Windows 桌面悬浮快捷文本管理工具，像素风图标 + 毛玻璃面板，支持分组管理和一键复制。Electron 桌面应用。',
  category: '效率工具',
  status: 'showcase',
  href: '/tools/',
  featured: false,
},
```

### 建议扩展类型定义

当前 `ToolStatus` 仅有 `'usable' | 'showcase'`。如果后续需要更细粒度的分类，建议扩展为：

```ts
export type ToolStatus = 'usable' | 'showcase' | 'local-only';
```

其中 `local-only` 表示仅本地使用、不在网站上展示的工具（如"短视频自动化整套"）。当前盘点中标记为 `no-private` 的工具建议不添加到 `tools.ts` 中。

---

## 四、后续建议

1. **优先实现**: 公众号排版助手 → MiniMax TTS 字幕 → 口播文案后处理（按实现难度从低到高）
2. **展示页设计**: 为 showcase 类工具设计统一的详情页模板，包含工具用途、运行环境、关键依赖、使用步骤、风险提示
3. **空目录清理**: 确认 `抖音私信同步/` 和 `公众号自动上传skill/` 是否需要保留
4. **截图准备**: 为 showcase 类工具准备截图或 GIF 演示
5. **API Key 安全**: 所有依赖 API Key 的工具（排版助手、TTS）必须在浏览器端让用户自行输入，不在源码中硬编码
6. **合规审查**: "短视频自动化整套"和"抖音视频自动上传"涉及的内容搬运/改写/自动发布功能存在显著的平台合规和法律风险，建议不在公开网站提及

---

> **盘点完成时间**: 2026-05-29
> **盘点方式**: 只读文件分析，未运行任何工具脚本
> **未修改任何原工具文件**
