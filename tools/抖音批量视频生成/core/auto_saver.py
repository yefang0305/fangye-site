"""
auto_saver.py
─────────────
统一的文案 / 音频自动保存工具。

文案保存路径：
  output/scripts/YYYY-MM-DD/HH-MM-SS_[类型]_[文案前缀].txt

音频保存路径：
  output/audio/YYYY-MM-DD/HH-MM-SS_tts[_预览].mp3
"""

import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path

from .config import get_app_dir

logger = logging.getLogger('AutoSaver')

SAVE_ROOT = 'output/scripts'
AUDIO_ROOT = 'output/audio'
PREVIEW_CHARS = 12


def _sanitize(text: str) -> str:
    """将文本处理成合法的文件名片段"""
    cleaned = re.sub(r'[^一-鿿\w]', '', text)
    return cleaned[:PREVIEW_CHARS]


def auto_save(text: str, category: str) -> str:
    if not text or not text.strip():
        return ''
    try:
        app_dir = Path(get_app_dir())
        today = datetime.now().strftime('%Y-%m-%d')
        ts = datetime.now().strftime('%H-%M-%S')
        preview = _sanitize(text.strip())
        save_dir = app_dir / SAVE_ROOT / today
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{ts}_{category}_{preview}.txt"
        filepath = save_dir / filename
        filepath.write_text(text.strip(), encoding='utf-8')
        logger.info('自动保存成功: %s', filepath)
        return str(filepath)
    except Exception as e:
        logger.error('自动保存失败: %s', e)
        return ''


def get_save_root() -> str:
    return str(Path(get_app_dir()) / SAVE_ROOT)


def auto_save_audio(src_path: str, text_preview: str = '') -> str:
    if not src_path:
        return ''
    src = Path(src_path)
    if not src.exists():
        logger.warning('auto_save_audio: 源文件不存在 %s', src_path)
        return ''
    try:
        app_dir = Path(get_app_dir())
        today = datetime.now().strftime('%Y-%m-%d')
        ts = datetime.now().strftime('%H-%M-%S')
        preview = _sanitize(text_preview.strip()) if text_preview else ''
        suffix = src.suffix or '.mp3'
        save_dir = app_dir / AUDIO_ROOT / today
        save_dir.mkdir(parents=True, exist_ok=True)
        name_parts = [ts, 'tts']
        if preview:
            name_parts.append(preview)
        filename = '_'.join(name_parts) + suffix
        dest = save_dir / filename
        shutil.copy2(str(src), str(dest))
        logger.info('音频自动保存成功: %s', dest)
        return str(dest)
    except Exception as e:
        logger.error('音频自动保存失败: %s', e)
        return ''
