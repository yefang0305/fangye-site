"""Smoke test for cover extractor — uses ffmpeg to generate a 1s test clip,
then extracts a frame from it. Skipped if ffmpeg is not findable."""
import subprocess
import pytest
from pathlib import Path

from publisher.cover_extractor import extract_first_frame, _find_ffmpeg


def _make_test_video(out_path: Path) -> bool:
    """Try to synthesize a test video. Playwright's bundled ffmpeg is
    minimal — try common codecs and skip if none work."""
    ffmpeg = _find_ffmpeg()
    for codec_args in [
        ["-c:v", "mpeg4"],
        ["-c:v", "libx264", "-pix_fmt", "yuv420p"],
        ["-c:v", "rawvideo", "-pix_fmt", "yuv420p"],
    ]:
        result = subprocess.run(
            [ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1",
             *codec_args, str(out_path)],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0 and out_path.is_file() and out_path.stat().st_size > 0:
            return True
    return False


def test_extract_first_frame_creates_jpeg(tmp_path):
    try:
        _find_ffmpeg()
    except RuntimeError:
        pytest.skip("ffmpeg not available")

    video = tmp_path / "test.mp4"
    if not _make_test_video(video):
        pytest.skip("bundled ffmpeg lacks any usable encoder for synthesizing a test clip")
    cover = extract_first_frame(str(video), str(tmp_path / "cover.jpg"))
    assert Path(cover).is_file()
    assert Path(cover).stat().st_size > 100  # some real bytes


def test_extract_missing_video_raises():
    with pytest.raises(FileNotFoundError):
        extract_first_frame("nonexistent.mp4")
