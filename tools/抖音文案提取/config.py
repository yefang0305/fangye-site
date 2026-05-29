from __future__ import annotations

from pathlib import Path
import argparse
import json


DEFAULT_MODEL = "large-v3"
DEFAULT_DEVICE = "cuda"
DEFAULT_COMPUTE_TYPE = "int8_float16"
DEFAULT_LANGUAGE = "zh"
DEFAULT_MODEL_DIR = str(Path.home() / ".douyin_asr" / "models")
DEFAULT_OUTPUT_DIR = str(Path.cwd() / "output")


def _env_or(key: str, default: str) -> str:
    import os
    return os.environ.get(key, default)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="douyin-asr",
        description="本地抖音口播文案提取工具（基于 faster-whisper）",
    )
    p.add_argument(
        "input",
        nargs="?",
        default=".",
        help="视频文件路径或包含视频的目录（默认: 当前目录）",
    )
    p.add_argument(
        "-m", "--model",
        default=_env_or("DOUYIN_ASR_MODEL", DEFAULT_MODEL),
        help=f"faster-whisper 模型名称 (默认: {DEFAULT_MODEL})",
    )
    p.add_argument(
        "-d", "--device",
        default=_env_or("DOUYIN_ASR_DEVICE", DEFAULT_DEVICE),
        choices=["cuda", "cpu"],
        help=f"推理设备 (默认: {DEFAULT_DEVICE})",
    )
    p.add_argument(
        "-c", "--compute-type",
        default=_env_or("DOUYIN_ASR_COMPUTE_TYPE", DEFAULT_COMPUTE_TYPE),
        help=f"计算精度 (默认: {DEFAULT_COMPUTE_TYPE})",
    )
    p.add_argument(
        "-l", "--language",
        default=_env_or("DOUYIN_ASR_LANGUAGE", DEFAULT_LANGUAGE),
        help=f"语言代码，auto 表示自动检测 (默认: {DEFAULT_LANGUAGE})",
    )
    p.add_argument(
        "--model-dir",
        default=_env_or("DOUYIN_ASR_MODEL_DIR", DEFAULT_MODEL_DIR),
        help=f"模型缓存目录 (默认: {DEFAULT_MODEL_DIR})",
    )
    p.add_argument(
        "-o", "--output-dir",
        default=_env_or("DOUYIN_ASR_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        help=f"输出目录 (默认: {DEFAULT_OUTPUT_DIR})",
    )
    p.add_argument(
        "--no-clean",
        action="store_true",
        help="跳过文本清洗（保留原始 ASR 输出）",
    )
    p.add_argument(
        "--ext",
        default="",
        help="按扩展名过滤视频文件，逗号分隔 (例如: .mp4,.mov)",
    )
    return p.parse_args(argv)


def discover_videos(input_path: str, ext_filter: str = "") -> list[Path]:
    p = Path(input_path).resolve()
    if p.is_file():
        return [p]
    if not p.is_dir():
        raise FileNotFoundError(f"路径不存在: {p}")

    exts = set()
    if ext_filter:
        exts = {e.strip().lower() for e in ext_filter.split(",") if e.strip()}
        if not all(e.startswith(".") for e in exts):
            raise ValueError("扩展名必须以 . 开头，例如: .mp4,.mov")

    from asr_engine import VIDEO_EXTENSIONS
    allowed = exts or VIDEO_EXTENSIONS
    videos = sorted(
        f for f in p.rglob("*")
        if f.suffix.lower() in allowed and f.is_file()
    )
    return videos


def write_outputs(
    output_dir: Path,
    stem: str,
    raw_text: str,
    cleaned_text: str,
    segments: list[dict],
    language: str,
    duration: float | None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / f"{stem}.txt"
    md_path = output_dir / f"{stem}.md"
    json_path = output_dir / f"{stem}.json"

    txt_path.write_text(cleaned_text or raw_text, encoding="utf-8")

    md_body = f"# {stem}\n\n"
    if language:
        md_body += f"**语言**: {language}\n\n"
    if duration is not None:
        md_body += f"**时长**: {duration:.1f}s\n\n"
    md_body += f"{cleaned_text or raw_text}\n\n---\n\n"
    if segments:
        md_body += "## 分段时间戳\n\n"
        for seg in segments:
            md_body += f"- [{seg['start']:.1f}s – {seg['end']:.1f}s] {seg['text']}\n"
    md_path.write_text(md_body.strip() + "\n", encoding="utf-8")

    json_payload = {
        "source": stem,
        "language": language,
        "duration": duration,
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "segments": segments,
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {".txt": txt_path, ".md": md_path, ".json": json_path}


def _build_config_namespace(args: argparse.Namespace) -> dict:
    return {
        "model_name": args.model,
        "device": args.device,
        "compute_type": args.compute_type,
        "language": args.language,
        "model_dir": args.model_dir,
    }
