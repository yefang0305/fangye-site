"""非推理测试：验证文件发现、参数解析、输出格式、清洗规则。

此测试不加载 faster-whisper 模型，不需要 FFmpeg，不执行 ASR 推理。
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

import config
from config import parse_args, discover_videos, write_outputs
from rule_cleaner import clean_transcript_rules


# ── 参数解析 ──────────────────────────────────────────────

def test_parse_args_defaults():
    args = parse_args([])
    assert args.model == config.DEFAULT_MODEL, f"model={args.model}"
    assert args.device == config.DEFAULT_DEVICE, f"device={args.device}"
    assert args.language == config.DEFAULT_LANGUAGE, f"language={args.language}"
    assert args.input == ".", f"input={args.input}"


def test_parse_args_custom():
    args = parse_args(["my_video.mp4", "-m", "small", "-d", "cpu", "-l", "auto", "--no-clean"])
    assert args.input == "my_video.mp4"
    assert args.model == "small"
    assert args.device == "cpu"
    assert args.language == "auto"
    assert args.no_clean is True


def test_parse_args_ext_filter():
    args = parse_args(["--ext", ".mp4,.mov"])
    assert args.ext == ".mp4,.mov"


def test_parse_args_output_dir():
    args = parse_args(["-o", "custom_output"])
    assert args.output_dir == "custom_output"


# ── 文件发现 ──────────────────────────────────────────────

def test_discover_videos_single_file(tmp_path: Path):
    f = tmp_path / "test.mp4"
    f.write_text("")
    videos = discover_videos(str(f))
    assert len(videos) == 1
    assert videos[0].name == "test.mp4"


def test_discover_videos_dir(tmp_path: Path):
    (tmp_path / "a.mp4").write_text("")
    (tmp_path / "b.mov").write_text("")
    (tmp_path / "not_video.txt").write_text("")
    videos = discover_videos(str(tmp_path))
    names = {v.name for v in videos}
    assert "a.mp4" in names
    assert "b.mov" in names
    assert "not_video.txt" not in names


def test_discover_videos_ext_filter(tmp_path: Path):
    (tmp_path / "a.mp4").write_text("")
    (tmp_path / "b.mov").write_text("")
    videos = discover_videos(str(tmp_path), ext_filter=".mp4")
    names = {v.name for v in videos}
    assert names == {"a.mp4"}


def test_discover_videos_nonexistent():
    try:
        discover_videos("Z:/nonexistent_path_12345")
        assert False, "should have raised"
    except FileNotFoundError:
        pass


def test_discover_videos_invalid_ext():
    try:
        discover_videos(".", ext_filter="mp4")  # no dot
        assert False, "should have raised"
    except ValueError:
        pass


# ── 输出写入 ──────────────────────────────────────────────

def test_write_outputs(tmp_path: Path):
    raw = "你好世界\n这是一段测试文本"
    cleaned = "你好世界。\n\n这是一段测试文本。"
    segments = [
        {"id": 0, "start": 0.0, "end": 2.5, "text": "你好世界"},
        {"id": 1, "start": 3.0, "end": 5.5, "text": "这是一段测试文本"},
    ]

    files = write_outputs(
        output_dir=tmp_path,
        stem="test_video",
        raw_text=raw,
        cleaned_text=cleaned,
        segments=segments,
        language="zh",
        duration=5.5,
    )

    assert files[".txt"].exists()
    assert files[".md"].exists()
    assert files[".json"].exists()

    txt = files[".txt"].read_text(encoding="utf-8")
    assert "你好世界" in txt

    md = files[".md"].read_text(encoding="utf-8")
    assert "# test_video" in md
    assert "2.5s" in md

    j = json.loads(files[".json"].read_text(encoding="utf-8"))
    assert j["language"] == "zh"
    assert j["duration"] == 5.5
    assert len(j["segments"]) == 2


def test_write_outputs_no_segments(tmp_path: Path):
    files = write_outputs(
        output_dir=tmp_path,
        stem="empty",
        raw_text="",
        cleaned_text="",
        segments=[],
        language="",
        duration=None,
    )
    assert files[".txt"].exists()
    assert files[".md"].exists()
    assert files[".json"].exists()


# ── 清洗规则 ──────────────────────────────────────────────

def test_clean_removes_filler_lines():
    result = clean_transcript_rules("嗯\n对吧\n你好世界")
    assert "嗯" not in result
    assert "对吧" not in result
    assert "你好世界" in result


def test_clean_removes_line_start_fillers():
    result = clean_transcript_rules("就是说这个东西很好用")
    assert result.startswith("这个东西")

    result2 = clean_transcript_rules("然后呢我们去吃饭")
    assert "然后呢" not in result2


def test_clean_adds_punctuation():
    result = clean_transcript_rules("你好吗")
    assert result.rstrip().endswith("？")

    result2 = clean_transcript_rules("今天天气真好")
    assert result2.rstrip().endswith("。")


def test_clean_corrections():
    result = clean_transcript_rules("这个食候我们应该吃饭")
    assert "这个时候" in result
    assert "食候" not in result


def test_clean_sales_filter():
    result = clean_transcript_rules("下单购买\n点击链接\n价格优惠")
    assert result == ""


def test_clean_empty():
    assert clean_transcript_rules("") == ""
    assert clean_transcript_rules("   \n  ") == ""


# ── 入口 ──────────────────────────────────────────────────

def run_all():
    import traceback

    tests = [
        fn for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]

    passed = 0
    failed = 0
    tmp_dir = Path(tempfile.mkdtemp(prefix="douyin_asr_test_"))

    for test_fn in tests:
        name = test_fn.__name__
        try:
            if "tmp_path" in test_fn.__code__.co_varnames:
                sub = tmp_dir / name
                sub.mkdir(exist_ok=True)
                test_fn(sub)
            else:
                test_fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception:
            failed += 1
            print(f"  FAIL  {name}")
            traceback.print_exc()

    # cleanup
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(run_all())
