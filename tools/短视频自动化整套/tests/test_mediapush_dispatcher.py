"""Smoke-test for the MediaPush dispatcher module.

Verifies the write_batch function creates the expected directory structure
and manifest.json without requiring MediaPush to be running.
"""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


class MediaPushDispatcherTests(unittest.TestCase):
    def test_write_batch_creates_batch_dir_with_manifest_and_videos(self):
        from automation_suite.mediapush_dispatcher import write_batch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "inbox"
            inbox.mkdir()

            # Create fake videos
            v1 = root / "video1.mp4"
            v2 = root / "video2.mp4"
            v1.write_bytes(b"fake mp4 content 1")
            v2.write_bytes(b"fake mp4 content 2")

            scheduled = datetime(2026, 5, 1, 7, 0, 0)
            batch_dir = write_batch(
                inbox_dir=inbox,
                video_paths=[v1, v2],
                scheduled_time=scheduled,
                slot_name="morning",
                move=False,
            )

            self.assertTrue(batch_dir.exists())
            manifest_path = batch_dir / "manifest.json"
            self.assertTrue(manifest_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], 1)
            self.assertEqual(manifest["scheduled_time"], "2026-05-01T07:00:00")
            self.assertEqual(len(manifest["videos"]), 2)
            self.assertIn("video1.mp4", manifest["videos"])
            self.assertIn("video2.mp4", manifest["videos"])
            self.assertEqual(manifest["source"], "videocut-batch-automation")

            # Source videos should still exist (copy mode)
            self.assertTrue(v1.exists())
            self.assertTrue(v2.exists())

            # Batch dir should contain video copies
            self.assertTrue((batch_dir / "video1.mp4").exists())
            self.assertTrue((batch_dir / "video2.mp4").exists())

    def test_write_batch_moves_videos_when_move_is_true(self):
        from automation_suite.mediapush_dispatcher import write_batch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "inbox"
            inbox.mkdir()

            v1 = root / "video_move.mp4"
            v1.write_bytes(b"move me")

            batch_dir = write_batch(
                inbox_dir=inbox,
                video_paths=[v1],
                scheduled_time=datetime.now(),
                slot_name="evening",
                move=True,
            )

            self.assertFalse(v1.exists())  # Should be moved
            self.assertTrue((batch_dir / "video_move.mp4").exists())

    def test_write_batch_raises_on_empty_paths(self):
        from automation_suite.mediapush_dispatcher import write_batch

        with self.assertRaises(ValueError):
            write_batch(
                inbox_dir="/tmp/inbox",
                video_paths=[],
                scheduled_time=datetime.now(),
                slot_name="morning",
            )

    def test_write_batch_raises_on_missing_video(self):
        from automation_suite.mediapush_dispatcher import write_batch

        with self.assertRaises(FileNotFoundError):
            write_batch(
                inbox_dir="/tmp/inbox",
                video_paths=["/nonexistent/video.mp4"],
                scheduled_time=datetime.now(),
                slot_name="morning",
            )


if __name__ == "__main__":
    unittest.main()
