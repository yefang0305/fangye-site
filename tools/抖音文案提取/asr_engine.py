from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile


VIDEO_EXTENSIONS = {
    ".3gp", ".avi", ".flv", ".m4v", ".mkv", ".mov", ".mp4",
    ".mpeg", ".mpg", ".rmvb", ".ts", ".vob", ".webm", ".wmv",
}


class LocalASRError(RuntimeError):
    pass


class LocalWhisperASREngine:
    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "int8_float16",
        language: str = "zh",
        model_dir: str | Path | None = None,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model_dir = Path(model_dir or (Path.home() / ".douyin_asr" / "models")).resolve()
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._set_model_env()

    def transcribe(self, video_path: str | Path) -> dict:
        source = Path(video_path)
        if not source.exists():
            raise LocalASRError(f"视频文件不存在: {source}")
        model = self._load_model()
        ffmpeg = self._find_ffmpeg()
        language = None if str(self.language).lower() == "auto" else self.language

        with tempfile.TemporaryDirectory(prefix="douyin_asr_") as temp_dir:
            source_for_asr = source
            if ffmpeg and source.suffix.lower() in VIDEO_EXTENSIONS:
                audio_path = Path(temp_dir) / f"{source.stem}.wav"
                self._extract_audio(ffmpeg, source, audio_path)
                source_for_asr = audio_path

            segments_iter, info = model.transcribe(
                str(source_for_asr),
                language=language,
                beam_size=5,
                vad_filter=True,
            )
            segments = [
                {
                    "id": segment.id,
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": segment.text.strip(),
                }
                for segment in segments_iter
            ]
        raw_text = "\n".join(item["text"] for item in segments if item["text"]).strip()
        return {
            "raw_text": raw_text,
            "segments": segments,
            "language": getattr(info, "language", ""),
            "duration": getattr(info, "duration", None),
        }

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise LocalASRError("faster-whisper 未安装，请运行: pip install faster-whisper") from exc
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def _set_model_env(self) -> None:
        os.environ.setdefault("HF_HOME", str(self.model_dir / "hf_home"))
        os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(self.model_dir / "huggingface"))
        os.environ.setdefault("HF_HUB_CACHE", str(self.model_dir / "huggingface"))
        os.environ.setdefault("XDG_CACHE_HOME", str(self.model_dir / "xdg_cache"))
        os.environ.setdefault("CT2_CACHE_DIR", str(self.model_dir / "ctranslate2"))

    def _find_ffmpeg(self) -> str | None:
        candidates = [
            shutil.which("ffmpeg"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return str(Path(candidate))
        return None

    @staticmethod
    def _extract_audio(ffmpeg: str, source: Path, target: Path) -> None:
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(target),
        ]
        subprocess.run(command, check=True)
