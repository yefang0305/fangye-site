# Goal
Analyze the source project at `J:\MagicTool\Standalone\VideoCut\video_tool` and produce a read-only inventory report for splitting its combined desktop workbench features into standalone tools for a personal website/tool collection.

The final report must be written to `J:\MagicTool\个人网站\tools\_拆分盘点\工具拆分盘点报告.md`.

# Allowed Scope
Read-only inspection is allowed under:
- `J:\MagicTool\Standalone\VideoCut\video_tool`
- `J:\MagicTool\个人网站\tools`

Writing is allowed only under:
- `J:\MagicTool\个人网站\tools\_拆分盘点`

The report should cover at least these source areas if present:
- Main desktop entrypoints: `main.py`, `standalone_editor.py`
- UI modules under `ui/`
- Core modules under `core/`
- Existing separate folders such as `image create`, `文案提取工具`, `video cut design`, and `auto`
- Build/package scripts and specs only as dependency/packaging evidence

# Forbidden Actions
- Do not modify, create, delete, move, format, or overwrite any file under `J:\MagicTool\Standalone\VideoCut\video_tool`.
- Do not copy implementation files into tool folders yet.
- Do not install dependencies, run package managers, launch GUI apps, or start long-running services.
- Do not edit existing tool folders except the allowed `_拆分盘点` folder.
- Do not make git commits, branch changes, resets, checkouts, or cleanup operations.
- Do not broaden the task into implementation or scaffolding.

# Acceptance Criteria
The report must include:
- A concise executive summary.
- A module/function inventory for all meaningful workbench features discovered.
- For each candidate tool: recommended output form (`web tool`, `standalone project`, `not recommended yet`, or `already separate candidate`), suggested destination under `J:\MagicTool\个人网站\tools`, source files/directories, dependencies, coupling/risk level, and rationale.
- A mapping to the existing empty destination folders where possible.
- A recommended phased extraction order, prioritizing low-risk and website-friendly tools first.
- Explicit notes about which features require local desktop access, FFmpeg, PyQt, browser automation, external APIs, authentication, or large model services.
- A verification section proving no source files were modified.

# Verification
Run these commands and include outcomes in the final report:
- `git status --short` from `J:\MagicTool\Standalone\VideoCut\video_tool` before analysis.
- `git status --short` from `J:\MagicTool\Standalone\VideoCut\video_tool` after report creation.
- A directory listing of `J:\MagicTool\个人网站\tools\_拆分盘点` showing the report file exists.

# Report Requirements
Claude Code must finish with exactly these report headings, in this order: Status, Role, Summary, Changed Files, Verification, Findings, Final Result, Risks Or Follow-ups.

Rules for those headings:
- Status: use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Role: use researcher.
- Summary: summarize the inventory work and the report created.
- Changed Files: list only files written under `J:\MagicTool\个人网站\tools\_拆分盘点`.
- Verification: list each verification command actually run and its observed outcome.
- Findings: summarize the most important module split findings.
- Final Result: must exactly match Status and use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Risks Or Follow-ups: list residual risks, unknowns, and recommended next steps.
