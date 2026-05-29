# Goal
Create a standalone web tool for extracting all Douyin profile作品 links from an input Douyin profile URL and exporting the result as Markdown.

Target output directory: J:\MagicTool\个人网站\tools\抖音主页链接采集.

# Allowed Scope
Read-only source inspection is allowed under:
- J:\MagicTool\Standalone\VideoCut\video_tool\core\benchmark_ingestion
- J:\MagicTool\Standalone\VideoCut\video_tool\requirements.txt
- J:\MagicTool\Standalone\VideoCut\video_tool\AGENTS.md

Writing is allowed only under:
- J:\MagicTool\个人网站\tools\抖音主页链接采集

Create a self-contained small web project. Prefer a Python backend plus simple browser UI. The tool should not import from the source project at runtime; copy/adapt only the minimal logic needed.

# Forbidden Actions
- Do not modify, delete, move, format, or overwrite any file under J:\MagicTool\Standalone\VideoCut\video_tool.
- Do not write outside J:\MagicTool\个人网站\tools\抖音主页链接采集.
- Do not install dependencies, run network calls against Douyin as verification, launch GUI apps, or start long-running services.
- Do not require secrets to be committed. Cookie paths or cookie text must be user-provided at runtime.
- Do not implement video downloading or ASR in this tool.

# Acceptance Criteria
The target folder contains a usable project with:
- A README in Chinese explaining what the tool does, setup, how to run, cookie requirements, and limitations.
- A dependency file.
- A browser UI where the user can enter a Douyin profile URL, optional cookies/cookie file settings, max pages/page size, then run extraction.
- Backend code that resolves profile URLs, extracts sec_uid, paginates Douyin post API responses, deduplicates links, and creates a Markdown export file.
- A safe output folder for generated Markdown documents.
- Unit tests or small verification scripts for pure parsing/export behavior without network access.
- No runtime import dependency on J:\MagicTool\Standalone\VideoCut\video_tool.

# Verification
Run and report outcomes:
- python -m compileall . from J:\MagicTool\个人网站\tools\抖音主页链接采集.
- A non-network test command for parsing/export behavior, for example python -m pytest if tests are included or a local script if pytest is not used.
- git status --short from J:\MagicTool\Standalone\VideoCut\video_tool after implementation to show the source project was not modified by this task.

# Report Requirements
Claude Code must finish with exactly these report headings, in this order: Status, Role, Summary, Changed Files, Verification, Findings, Final Result, Risks Or Follow-ups.

Rules for those headings:
- Status: use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Role: use implementer.
- Changed Files: list only files written under J:\MagicTool\个人网站\tools\抖音主页链接采集.
- Verification: list each verification command actually run and observed outcome.
- Final Result: must exactly match Status.
