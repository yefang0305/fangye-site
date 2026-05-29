"""Drop a batch of generated videos into MediaPush's inbox folder.

Writes a `manifest.json` describing the batch (scheduled time + file list)
and moves the video files into the batch directory. MediaPush's
`InboxWatcher` will pick the batch up within seconds and submit it to its
publish queue.

Format contract (must stay in sync with publisher/inbox_watcher.py):

    inbox/<YYYYMMDD-HHMMSS>-<slot>/
        manifest.json   {version, batch_id, scheduled_time, videos, ...}
        <video1>.mp4
        <video2>.mp4
        ...
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


MANIFEST_VERSION = 1
SOURCE_TAG = "videocut-batch-automation"


def write_batch(
    inbox_dir: str | Path,
    video_paths: list[str | Path],
    scheduled_time: datetime,
    slot_name: str,
    *,
    move: bool = True,
) -> Path:
    """Create a batch directory under inbox_dir, move (or copy) videos into
    it, and write manifest.json atomically.

    Args:
        inbox_dir: MediaPush inbox root (must already exist or be createable)
        video_paths: source video files (must all exist as files)
        scheduled_time: when MediaPush should publish
        slot_name: 'morning' / 'noon' / 'evening' — appears in batch dir name
                   for human readability
        move: if True, source videos are moved (faster, no duplicate disk
              usage). If False, copied via shutil.copy2.

    Returns:
        Path to the created batch directory.

    Raises:
        FileNotFoundError if any source video is missing.
        ValueError if video_paths is empty.
    """
    if not video_paths:
        raise ValueError("video_paths must not be empty")

    sources = [Path(p) for p in video_paths]
    for src in sources:
        if not src.is_file():
            raise FileNotFoundError(f"video not found: {src}")

    inbox = Path(inbox_dir)
    inbox.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_id = f"{stamp}-{slot_name}"
    batch_dir = inbox / batch_id
    # Avoid clobbering on rapid-fire calls within the same second
    suffix = 1
    while batch_dir.exists():
        suffix += 1
        batch_dir = inbox / f"{batch_id}-{suffix}"
        if suffix > 50:
            raise RuntimeError(f"too many collisions creating batch dir under {inbox}")
    batch_dir.mkdir(parents=True)

    # Move/copy videos (preserving original filenames)
    final_names: list[str] = []
    for src in sources:
        dst = batch_dir / src.name
        if dst.exists():
            # Disambiguate within batch (rare — only if two source files share name)
            stem, ext = dst.stem, dst.suffix
            i = 2
            while dst.exists():
                dst = batch_dir / f"{stem}__{i}{ext}"
                i += 1
        if move:
            shutil.move(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        final_names.append(dst.name)

    manifest = {
        "version": MANIFEST_VERSION,
        "batch_id": batch_dir.name,
        "scheduled_time": scheduled_time.isoformat(timespec="seconds"),
        "videos": final_names,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": SOURCE_TAG,
    }
    # Atomic write: tmp file then rename so the watcher never sees a half-written manifest
    tmp = batch_dir / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(batch_dir / "manifest.json")
    return batch_dir
