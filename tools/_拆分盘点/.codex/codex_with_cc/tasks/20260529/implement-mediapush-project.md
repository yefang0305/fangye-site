# Goal
Create an independent GitHub-ready project package for the MediaPush publishing workbench.

Source project: `J:\MagicTool\emdia\MediaPush`.
Target output directory: `J:\MagicTool\个人网站\tools\抖音视频自动上传`.

The package should preserve the desktop publisher workflow: account management, inbox watcher, publish queue, Douyin publisher automation, history panel, message panel, cleanup tools, and tests/docs where useful.

# Allowed Scope
Read-only source inspection is allowed under:
- `J:\MagicTool\emdia\MediaPush`
- `J:\MagicTool\Standalone\VideoCut\video_tool` only for integration notes if needed

Writing is allowed only under:
- `J:\MagicTool\个人网站\tools\抖音视频自动上传`

You may copy/adapt source files into the target. Preserve project structure when practical.

# Forbidden Actions
- Do not modify, delete, move, format, or overwrite any file under `J:\MagicTool\emdia\MediaPush`.
- Do not modify, delete, move, format, or overwrite any file under `J:\MagicTool\Standalone\VideoCut\video_tool`.
- Do not write outside `J:\MagicTool\个人网站\tools\抖音视频自动上传`.
- Do not copy `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `logs`, `tmp`, live `profiles`, private `.env`, runtime `data` caches, inbox videos, browser profile data, cookies, or account secrets.
- Do not install dependencies, launch browsers, run GUI apps, or run real publishing automation.

# Acceptance Criteria
The target directory must contain a GitHub-ready independent project package with:
- MediaPush application source (`main.py`, `account`, `db`, `publisher`, `mediapush_ui`, selected `tests`, selected `docs`).
- `pyproject.toml` or dependency file.
- `.env.example` replacing private `.env` values.
- `.gitignore` excluding profiles, logs, tmp, inbox, data caches, cookies, credentials, browser profiles, caches, and venv.
- Chinese `README.md` explaining value, supported workflows, setup, run command, account/profile setup, risks/limitations around platform automation and verification, and relation to the original VideoCut dispatch flow.
- Non-destructive verification via compile/import/tests that do not open browser or publish.

# Verification
Run and report outcomes:
- `python -m compileall .` from `J:\MagicTool\个人网站\tools\抖音视频自动上传` using any available Python.
- Run a safe subset of tests if feasible without external browser/platform access; otherwise explain why skipped and run import sanity checks.
- A file listing proving excluded runtime/private directories were not copied.
- `git status --short` from `J:\MagicTool\emdia\MediaPush` after implementation to show the source project was not modified by this task.

# Report Requirements
Claude Code must finish with exactly these report headings, in this order: Status, Role, Summary, Changed Files, Verification, Findings, Final Result, Risks Or Follow-ups.

Rules for those headings:
- Status: use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Role: use implementer.
- Changed Files: list only files written under `J:\MagicTool\个人网站\tools\抖音视频自动上传`.
- Verification: list each verification command actually run and observed outcome.
- Final Result: must exactly match Status.
