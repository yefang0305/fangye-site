# Goal
Create a standalone local-ASR project for importing local Douyin video files and extracting口播文案 with a local faster-whisper model.

Target output directory: J:\MagicTool\个人网站\tools\抖音文案提取.

# Allowed Scope
Read-only source inspection is allowed under:
- J:\MagicTool\Standalone\VideoCut\video_tool\core\benchmark_ingestion\local_asr_engine.py
- J:\MagicTool\Standalone\VideoCut\video_tool\core\benchmark_ingestion\rule_cleaner.py
- J:\MagicTool\Standalone\VideoCut\video_tool\文案提取工具
- J:\MagicTool\Standalone\VideoCut\video_tool\requirements.txt
- J:\MagicTool\Standalone\VideoCut\video_tool\AGENTS.md

Writing is allowed only under:
- J:\MagicTool\个人网站\tools\抖音文案提取

Create a self-contained local project. It may include CLI and/or a small local web UI, but it must work as a local project because faster-whisper models and FFmpeg are local dependencies. The tool should not import from the source project at runtime; copy/adapt only the minimal logic needed.

# Forbidden Actions
- Do not modify, delete, move, format, or overwrite any file under J:\MagicTool\Standalone\VideoCut\video_tool.
- Do not write outside J:\MagicTool\个人网站\tools\抖音文案提取.
- Do not install dependencies, download models, run expensive ASR inference, launch GUI apps, or start long-running services.
- Do not commit model files, videos, audio extracts, API keys, or large binary outputs.
- Do not implement Douyin crawling or video downloading in this tool.

# Acceptance Criteria
The target folder contains a usable project with:
- A README in Chinese explaining setup, FFmpeg requirement, faster-whisper model choices, CPU/GPU settings, and how to run batch extraction.
- A dependency file including aster-whisper and needed support libraries.
- A CLI entrypoint that accepts one video file or a folder of videos, extracts/normalizes audio with FFmpeg, transcribes locally, and writes .md, .txt, and .json outputs.
- Clear configuration for model name, device, compute type, language, output directory, and model cache directory.
- A small non-inference test or verification script for file discovery, output formatting, and command/config parsing.
- No runtime import dependency on J:\MagicTool\Standalone\VideoCut\video_tool.

# Verification
Run and report outcomes:
- python -m compileall . from J:\MagicTool\个人网站\tools\抖音文案提取.
- A non-inference test command for discovery/formatting/config behavior, for example python -m pytest if tests are included or a local script if pytest is not used.
- git status --short from J:\MagicTool\Standalone\VideoCut\video_tool after implementation to show the source project was not modified by this task.

# Report Requirements
Claude Code must finish with exactly these report headings, in this order: Status, Role, Summary, Changed Files, Verification, Findings, Final Result, Risks Or Follow-ups.

Rules for those headings:
- Status: use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Role: use implementer.
- Changed Files: list only files written under J:\MagicTool\个人网站\tools\抖音文案提取.
- Verification: list each verification command actually run and observed outcome.
- Final Result: must exactly match Status.
