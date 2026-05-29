from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


class ExternalASRError(RuntimeError):
    pass


class ExternalBatchASREngine:
    """ASR engine that delegates to an external batch_asr.py script.

    Useful when the ASR environment is managed separately (e.g., a dedicated
    venv with faster-whisper or a remote ASR server). The external script
    receives input/output directories and produces txt/json/srt outputs.
    """

    def __init__(
        self,
        asr_root: str | Path,
        python_executable: str | Path | None = None,
        model: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "int8_float16",
        language: str = "zh",
        timeout: int = 7200,
    ):
        self.asr_root = Path(asr_root).resolve()
        self.python_executable = str(
            python_executable
            or self.asr_root / ".venv" / "Scripts" / "python.exe"
        )
        self.model = model
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.timeout = timeout

    def transcribe(self, video_path: str | Path) -> dict:
        source = Path(video_path).resolve()
        if not source.exists():
            raise ExternalASRError(f"视频文件不存在: {source}")
        script_path = self.asr_root / "scripts" / "batch_asr.py"
        if not script_path.exists():
            raise ExternalASRError(f"未找到本地 ASR 脚本: {script_path}")
        if not Path(self.python_executable).exists() and shutil.which(self.python_executable) is None:
            raise ExternalASRError(f"未找到本地 ASR Python: {self.python_executable}")

        with tempfile.TemporaryDirectory(prefix="benchmark_external_asr_") as temp_dir:
            temp_root = Path(temp_dir)
            input_dir = temp_root / "input"
            txt_dir = temp_root / "txt"
            json_dir = temp_root / "json"
            srt_dir = temp_root / "srt"
            logs_dir = temp_root / "logs"
            for directory in [input_dir, txt_dir, json_dir, srt_dir, logs_dir]:
                directory.mkdir(parents=True, exist_ok=True)

            copied_video = input_dir / source.name
            shutil.copy2(source, copied_video)

            command = [
                self.python_executable,
                str(script_path),
                "--input",
                str(input_dir),
                "--txt",
                str(txt_dir),
                "--json",
                str(json_dir),
                "--srt",
                str(srt_dir),
                "--logs",
                str(logs_dir),
                "--model",
                self.model,
                "--device",
                self.device,
                "--compute-type",
                self.compute_type,
                "--language",
                self.language,
                "--limit",
                "1",
                "--force",
            ]
            result = subprocess.run(
                command,
                cwd=str(self.asr_root),
                text=True,
                capture_output=True,
                timeout=self.timeout,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                raise ExternalASRError(f"本地 ASR 执行失败: {detail[:1200]}")

            txt_path = txt_dir / f"{self._safe_stem(copied_video)}.txt"
            json_path = json_dir / f"{self._safe_stem(copied_video)}.json"
            raw_text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
            payload = {}
            if json_path.exists():
                payload = json.loads(json_path.read_text(encoding="utf-8"))

            segments = payload.get("segments", [])
            if not raw_text:
                raw_text = "\n".join(str(item.get("text", "")).strip() for item in segments).strip()
            if not raw_text:
                raise ExternalASRError("本地 ASR 未生成文案")

            return {
                "raw_text": raw_text,
                "segments": segments,
                "language": payload.get("language", ""),
                "duration": payload.get("duration"),
            }

    @staticmethod
    def _safe_stem(path: Path) -> str:
        import re

        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", path.stem).strip()
        return stem or "untitled"


def create_default_asr_engine():
    """Create the best available ASR engine. Tries external batch ASR first,
    then falls back to local faster-whisper."""
    from .local_asr_engine import LocalWhisperASREngine

    return LocalWhisperASREngine()
