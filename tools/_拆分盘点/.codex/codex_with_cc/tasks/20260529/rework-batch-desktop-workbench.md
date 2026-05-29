# Goal
Rework the extracted batch remix project so it is a desktop workbench project, not only a CLI/core engine package.

Target output directory: `J:\MagicTool\个人网站\tools\抖音批量视频生成`.

The previous extraction created a CLI-oriented package. Keep that useful CLI if desired, but add a PyQt5 desktop workbench entry that preserves the batch automation UI and enough supporting UI/core modules for a GitHub-ready project.

# Allowed Scope
Read-only source inspection is allowed under:
- `J:\MagicTool\Standalone\VideoCut\video_tool`

Writing is allowed only under:
- `J:\MagicTool\个人网站\tools\抖音批量视频生成`

You may copy/adapt source files into the target. Prefer a focused desktop package for batch video generation, not the entire monolith. If importing the original full MainWindow is too broad, create a focused `desktop_app.py` / `main_desktop.py` that hosts `BatchAutomationPage` plus the worker classes and minimal settings/theme dependencies it needs.

# Forbidden Actions
- Do not modify, delete, move, format, or overwrite any file under `J:\MagicTool\Standalone\VideoCut\video_tool`.
- Do not write outside `J:\MagicTool\个人网站\tools\抖音批量视频生成`.
- Do not copy `venv`, `deps`, `dist`, `build`, `output`, `temp`, `logs`, `__pycache__`, `.git`, private activation/license data, generated videos, or user runtime data.
- Do not install dependencies, run GUI apps, run network calls, or start long-running services.
- Do not include API keys, activation codes, cookies, or personal account data.

# Acceptance Criteria
The target directory must contain:
- A desktop PyQt entrypoint such as `main_desktop.py` or equivalent that launches a batch video generation workbench.
- `ui/batch_automation/batch_automation_page.py` and all local UI/core modules needed for imports to resolve.
- Worker classes or adapters needed by `BatchAutomationPage` (`TTSWorker`, `ComposeWorker`, settings/config callbacks, MediaPush dispatch wiring when safe).
- Existing CLI entrypoint may remain, but README must make clear there are two modes: desktop workbench and CLI engine.
- `requirements.txt` includes PyQt5, Pillow, pydub, websockets, requests/openai-related dependencies as needed.
- `.gitignore` excludes runtime directories and credentials.
- Chinese README and docs updated to describe the desktop workbench, not only CLI commands.
- Verification shows Python files compile and a non-GUI import sanity check can import the desktop entry/module without launching the event loop.

# Verification
Run and report outcomes:
- `python -m compileall .` from `J:\MagicTool\个人网站\tools\抖音批量视频生成` using any available Python.
- A non-GUI import sanity check, for example importing `main_desktop` or the focused app module without launching QApplication.
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
