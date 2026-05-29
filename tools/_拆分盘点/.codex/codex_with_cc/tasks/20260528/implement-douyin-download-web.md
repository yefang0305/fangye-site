# Goal
Create a standalone web tool for batch downloading Douyin videos from one or more作品 links.

Target output directory: J:\MagicTool\个人网站\tools\抖音视频下载.

# Allowed Scope
Read-only source inspection is allowed under:
- J:\MagicTool\Standalone\VideoCut\video_tool\core\benchmark_ingestion
- J:\MagicTool\Standalone\VideoCut\video_tool\core\script_extractor
- J:\MagicTool\Standalone\VideoCut\video_tool\requirements.txt
- J:\MagicTool\Standalone\VideoCut\video_tool\AGENTS.md

Writing is allowed only under:
- J:\MagicTool\个人网站\tools\抖音视频下载

Create a self-contained small web project. Prefer a Python backend plus simple browser UI. The tool should not import from the source project at runtime; copy/adapt only the minimal logic needed.

# Forbidden Actions
- Do not modify, delete, move, format, or overwrite any file under J:\MagicTool\Standalone\VideoCut\video_tool.
- Do not write outside J:\MagicTool\个人网站\tools\抖音视频下载.
- Do not install dependencies, run network downloads as verification, launch GUI apps, or start long-running services.
- Do not commit cookies, API keys, downloaded videos, or large binary outputs.
- Do not implement profile crawling or ASR in this tool.

# Acceptance Criteria
The target folder contains a usable project with:
- A README in Chinese explaining setup, running, URL input format, cookie options, output directory, and common Douyin/yt-dlp failure modes.
- A dependency file including yt-dlp and the chosen web framework.
- A browser UI where the user can paste multiple Douyin video URLs, choose optional cookie file/browser cookie source, choose output folder, and start batch download.
- Backend code that validates URLs, deduplicates batch input, downloads sequentially with yt-dlp, records per-URL status, and exposes/downloads a Markdown or JSON run report.
- Safe output folders for videos and reports.
- Unit tests or verification scripts for URL parsing, deduplication, report generation, and downloader option construction without doing real network downloads.
- No runtime import dependency on J:\MagicTool\Standalone\VideoCut\video_tool.

# Verification
Run and report outcomes:
- python -m compileall . from J:\MagicTool\个人网站\tools\抖音视频下载.
- A non-network test command for URL parsing/report behavior, for example python -m pytest if tests are included or a local script if pytest is not used.
- git status --short from J:\MagicTool\Standalone\VideoCut\video_tool after implementation to show the source project was not modified by this task.

# Report Requirements
Claude Code must finish with exactly these report headings, in this order: Status, Role, Summary, Changed Files, Verification, Findings, Final Result, Risks Or Follow-ups.

Rules for those headings:
- Status: use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Role: use implementer.
- Changed Files: list only files written under J:\MagicTool\个人网站\tools\抖音视频下载.
- Verification: list each verification command actually run and observed outcome.
- Final Result: must exactly match Status.
