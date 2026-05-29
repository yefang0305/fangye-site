"""Extract the first frame of a video as a JPEG cover image.

Uses the ffmpeg binary that ships with Playwright (saves us a separate
dependency). Looks up the binary at import time.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from pathlib import Path


# Project-local tmp dir so we never write to C:\\Users\\...\\AppData\\Local\\Temp
_TMP_DIR = Path(__file__).resolve().parent.parent / "tmp"


def _find_ffmpeg() -> str:
    """Locate a full-codec ffmpeg binary.

    Preference order:
      1. imageio-ffmpeg's bundled static build (full codecs, in our .venv)
      2. System PATH ffmpeg
      3. Playwright's bundled ffmpeg (last resort — minimal codecs, may fail
         on common MP4s)
    """
    # 1. imageio-ffmpeg (full ffmpeg, on J: drive inside .venv)
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).is_file():
            return exe
    except Exception:
        pass

    # 2. System PATH
    from shutil import which
    sys_ffmpeg = which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    # 3. Playwright bundled ffmpeg (minimal — kept as last resort)
    pw_root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if pw_root:
        for p in Path(pw_root).glob("ffmpeg-*/ffmpeg-*.exe"):
            return str(p)

    raise RuntimeError(
        "ffmpeg not found. Run `uv pip install imageio-ffmpeg` in this venv."
    )


def extract_first_frame(video_path: str, out_path: str | None = None) -> str:
    """Extract the first frame of `video_path` and save as JPEG.

    Returns the absolute path of the cover image. If `out_path` is None,
    creates a temp file (caller is responsible for cleanup if desired —
    OS will clean temp dir eventually).
    """
    video = Path(video_path)
    if not video.is_file():
        raise FileNotFoundError(f"video not found: {video_path}")

    if out_path is None:
        _TMP_DIR.mkdir(parents=True, exist_ok=True)
        out_path = str(_TMP_DIR / f"{video.stem}_cover_{uuid.uuid4().hex[:8]}.jpg")
    out_abs = str(Path(out_path).resolve())

    ffmpeg = _find_ffmpeg()
    cmd = [
        ffmpeg,
        "-y",                # overwrite output
        "-i", str(video.resolve()),
        "-frames:v", "1",    # exactly one frame
        "-q:v", "2",         # high JPEG quality
        out_abs,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}): {result.stderr[-400:]}")
    if not Path(out_abs).is_file() or Path(out_abs).stat().st_size == 0:
        raise RuntimeError("ffmpeg produced no output file")
    return out_abs
