"""Benchmark video ingestion and script library helpers.

This package provides the core pipeline for:
- Video link recognition and routing (抖音, B站, YouTube, 小红书, 快手)
- Profile expansion (extracting all video links from an account)
- Video download (yt-dlp + CR TubeGet fallback for 抖音)
- Local ASR via faster-whisper
- Text cleaning and adaptation review via LLM
- Script library management
- MediaPush dispatch integration
"""

