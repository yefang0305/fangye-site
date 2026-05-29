# Goal
Create an independent GitHub-ready project package for the full batch remix/video generation workbench.

Target output directory: `J:\MagicTool\个人网站\tools\抖音批量视频生成`.

The package should preserve the valuable desktop workflow: script/TTS or uploaded audio, segmentation, material random matching, BGM, subtitles, cover/title handling, and batch automation queue. This is a project extraction, not a web rewrite.

# Allowed Scope
Read-only source inspection is allowed under:
- `J:\MagicTool\Standalone\VideoCut\video_tool`

Writing is allowed only under:
- `J:\MagicTool\个人网站\tools\抖音批量视频生成`

You may copy/adapt source files into the target. Preserve functionality as much as practical, but prioritize a clean GitHub-ready project over copying runtime junk.

# Forbidden Actions
- Do not modify, delete, move, format, or overwrite any file under `J:\MagicTool\Standalone\VideoCut\video_tool`.
- Do not write outside `J:\MagicTool\个人网站\tools\抖音批量视频生成`.
- Do not copy `venv`, `deps`, `dist`, `build`, `output`, `temp`, `logs`, `__pycache__`, `.git`, private activation/license data, generated videos, or user runtime data.
- Do not install dependencies, run GUI apps, run network calls, or start long-running services.
- Do not include API keys, activation codes, cookies, or personal account data.

# Acceptance Criteria
The target directory must contain a GitHub-ready independent project package with:
- Python entrypoint(s) appropriate for the batch remix workbench.
- Required `core/` and `ui/` modules copied/adapted so imports are internally coherent.
- `requirements.txt` or `pyproject.toml` with needed dependencies.
- `.gitignore` excluding venv, caches, logs, output, temp, credentials, model/binary/runtime artifacts.
- A Chinese `README.md` that explains product value, major features, architecture, setup, run command, FFmpeg requirement, API configuration, packaging notes, and known limitations.
- A `docs/` folder or architecture note explaining what was extracted from the original workbench and what was intentionally excluded.
- Small non-GUI verification, such as compileall and import sanity checks, that does not require API keys or FFmpeg execution.

# Verification
Run and report outcomes:
- `python -m compileall .` from `J:\MagicTool\个人网站\tools\抖音批量视频生成` using any available Python.
- A file listing proving no excluded runtime directories were copied.
- `git status --short` from `J:\MagicTool\Standalone\VideoCut\video_tool` after implementation to show the source project was not modified by this task.

# Report Requirements
Claude Code must finish with exactly these report headings, in this order: Status, Role, Summary, Changed Files, Verification, Findings, Final Result, Risks Or Follow-ups.

Rules for those headings:
- Status: use one of DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED, FAIL.
- Role: use implementer.
- Changed Files: list only files written under `J:\MagicTool\个人网站\tools\抖音批量视频生成`.
- Verification: list each verification command actually run and observed outcome.
- Final Result: must exactly match Status.
