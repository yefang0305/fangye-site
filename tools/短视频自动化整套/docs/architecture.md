# 短视频自动化工具集 — 架构文档

## 数据流

```
Markdown 链接源 (.md)
    │
    ▼
[link_router.py]  ── 识别链接类型 (单视频 / 账号 / 合集 / 播放列表)
    │
    ├── 单视频链接 ──────────────────────────┐
    │                                        │
    ├── 账号链接 ──► [douyin_profile.py] ──┤
    │                   展开全部作品链接       │
    │                                        │
    └── 合集链接 ──► (TODO)                  │
                                             │
    ┌────────────────────────────────────────┘
    ▼
[orchestrator.py]  ── 编排整体流程
    │
    ├── 选择链接（skip 已处理，应用 limit）
    │
    ▼
[pipeline.py]  ── 单链接处理流水线
    │
    ├── 1. [downloader.py]    视频下载
    │       ├── yt-dlp（主下载器）
    │       └── CR TubeGet（抖音 fallback / 优先）
    │
    ├── 2. [local_asr_engine.py]  本地 ASR (faster-whisper)
    │    或 [external_asr_engine.py]  外部 ASR 脚本
    │
    ├── 3. [rule_cleaner.py]   规则清洗
    │       ├── 修复同音字
    │       ├── 去除口癖
    │       ├── 添加标点
    │       ├── 分段落
    │       └── 过滤带货
    │
    ├── 4. [adaptation_reviewer.py]  适配审查 (LLM)
    │       ├── keep   → 直接入库
    │       ├── rewrite → 改写后入库
    │       └── reject  → 拒绝入库
    │
    ├── 5. [llm_cleaner.py]   LLM 文案清洗（可选）
    │
    └── 6. [script_library.py]  脚本库存储
            ├── JSON 索引 (library.json)
            └── TXT 文件 (txt/*.txt)
```

## 状态追踪

```
[state_store.py]
    │
    └── ingestion_state.json
        {
          "urls": {
            "<url_hash>": {
              "status": "downloading|downloaded|asr_done|llm_done|adaptation_rejected|permanent_failed",
              "failure_count": N,
              ...
            }
          }
        }
```

状态流转：
```
downloading → downloaded → asr_done → llm_done  (成功)
                                   → adaptation_rejected (拒绝)
failed → failed → ... → permanent_failed (达到 max_failures)
```

## MediaPush 集成

```
[mediapush_dispatcher.py]
    │
    └── write_batch(inbox_dir, video_paths, scheduled_time, slot_name)
        │
        ├── 创建批次目录 inbox/<timestamp>-<slot>/
        ├── 移动/复制视频文件
        └── 写入 manifest.json（原子写入）
            │
            ▼
        MediaPush InboxWatcher 自动拾取 → 发布队列 → 各平台发布
```

## 关键设计决策

### 1. 保守适配审查
审查策略为"保守过滤，宁可拒绝"。这是为了防止不适合的内容进入批量生产链路。
- 默认拒绝过往经历、作者自述、女性视角
- rewrite 仅用于轻微可迁移问题
- 审查失败时默认 reject（fails-closed）

### 2. 抖音双重下载策略
- 有 CR TubeGet 时优先使用直链解析（绕过 yt-dlp Cookie 问题）
- yt-dlp 失败时自动回退到 CR TubeGet
- 两者都需要抖音 Cookie

### 3. 脚本库设计
- 索引（JSON）与内容（TXT）分离
- 索引不存储 raw_script 和 cleaned_script，只存元数据
- 支持按状态查询、标记已使用

### 4. 状态持久化
- 每个 URL 的处理状态持久化到 JSON
- 支持断点续跑
- 失败计数达到 max_failures 后标记为 permanent_failed
