# Goal
Create an independent GitHub-ready project package for the end-to-end short-video automation suite.

Target output directory: `J:\MagicTool\个人网站\tools\短视频自动化整套`.

This package should present the larger automation system as a project: benchmark account/profile ingestion, profile link expansion, video download via CR TubeGet/yt-dlp, local/external ASR, text cleaning/review, script library, batch generation handoff, and optional publisher dispatch. It should be a cohesive project package/documented toolkit, not a lightweight website widget.

# Allowed Scope
Read-only source inspection is allowed under:
- `J:\MagicTool\Standalone\VideoCut\video_tool`
- `J:\MagicTool\emdia\MediaPush` for dispatch integration notes only
- Existing extracted tools under `J:\MagicTool\个人网站\tools` for references only

Writing is allowed only under:
- `J:\MagicTool\个人网站\tools\短视频自动化整套`

You may copy/adapt source files into the target, with focus on automation pipeline modules and documentation.

# Forbidden Actions
- Do not modify, delete, move, format, or overwrite any file under `J:\MagicTool\Standalone\VideoCut\video_tool`.
- Do not modify, delete, move, format, or overwrite any file under `J:\MagicTool\emdia\MediaPush`.
- Do not write outside `J:\MagicTool\个人网站\tools\短视频自动化整套`.
- Do not copy `venv`, `deps`, `dist`, `build`, generated videos, `output`, `temp`, `logs`, `.git`, `__pycache__`, private credentials, cookies, browser profiles, or user data.
- Do not install dependencies, run network calls, run ASR models, launch browsers, or start services.

# Acceptance Criteria
The target directory must contain a GitHub-ready independent project package with:
- Automation pipeline source copied/adapted from `core/benchmark_ingestion`, `auto_batch_from_txt.py`, `core/mediapush_dispatcher.py`, relevant tests/docs, and minimal support modules.
- A clear package structure such as `automation_suite/`, `docs/`, `examples/`, and `tests/`.
- `requirements.txt` or `pyproject.toml` covering yt-dlp, faster-whisper, requests, openai-compatible LLM dependencies where applicable.
- `.env.example` and `.gitignore` for credentials/runtime artifacts.
- Chinese `README.md` explaining the full pipeline, architecture, setup, run examples, how it connects to batch generation and MediaPush, and which parts require local models/API keys/cookies/CR TubeGet.
- Example input/output files that are synthetic and safe to commit.
- Non-network/non-ASR tests or verification scripts for parsing, state store, script library, and routing behavior.

# Verification
Run and report outcomes:
- `python -m compileall .` from `J:\MagicTool\个人网站\tools\短视频自动化整套` using any available Python.
- Run safe non-network tests if included.
- A file listing proving excluded runtime/private directories were not copied.
- `git status --short` from `J:\MagicTool\Standalone\VideoCut\video_tool` after implementation to show the source project was not modified by this task.

# Report Requirements
Claude Code must finish with exactly these report headings, in this order: Status, Role, Summary, Changed Files, Verification, Findings, Final Result, Risks Or Follow-ups.

Rules for those headings:
- Status: use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Role: use implementer.
- Changed Files: list only files written under `J:\MagicTool\个人网站\tools\短视频自动化整套`.
- Verification: list each verification command actually run and observed outcome.
- Final Result: must exactly match Status.
