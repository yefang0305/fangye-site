"""Drop a batch of generated videos into MediaPush's inbox folder.

Writes a `manifest.json` describing the batch (scheduled time + file list)
and moves the video files into the batch directory.
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
    """Create a batch directory under inbox_dir, move videos into it,
    and write manifest.json atomically.

    Args:
        inbox_dir: MediaPush inbox root (must exist or be creatable)
        video_paths: source video files
        scheduled_time: when MediaPush should publish
        slot_name: 'morning' / 'noon' / 'evening'
        move: if True, source videos are moved (faster, no duplicate disk usage)

    Returns:
        Path to the created batch directory.
    """
    inbox = Path(inbox_dir)
    inbox.mkdir(parents=True, exist_ok=True)

    ts = scheduled_time.strftime("%Y%m%d-%H%M%S")
    batch_dir = inbox / f"{ts}-{slot_name}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    video_entries = []
    for vp in video_paths:
        src = Path(vp)
        if not src.exists():
            continue
        dest = batch_dir / src.name
        if move:
            shutil.move(str(src), str(dest))
        else:
            shutil.copy2(str(src), str(dest))
        video_entries.append(
            {
                "filename": src.name,
                "source_tag": SOURCE_TAG,
            }
        )

    manifest = {
        "version": MANIFEST_VERSION,
        "batch_id": batch_dir.name,
        "scheduled_time": scheduled_time.isoformat(),
        "created_at": datetime.now().isoformat(),
        "source": SOURCE_TAG,
        "videos": video_entries,
    }

    manifest_path = batch_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return batch_dir
