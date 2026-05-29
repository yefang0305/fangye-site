"""
text_segmenter.py - 基于 TTS 字级时间戳的文案分段
────────────────────────────────────────────────
将文案按句子自动生成视频分段。

核心逻辑：
  1. 按标点将文案拆成句子
  2. 从字级时间戳查每句的 start / end 时间
  3. 合并时长过短的句子，直到满足最短段落时长
  4. 最后一段若仍太短，并入前一段
"""

import re
import logging

logger = logging.getLogger("TextSegmenter")

END_PUNCTUATION = set("。！？…！？")
MID_PUNCTUATION = set("，,；;")
ALL_PUNCTUATION = set("。！？…，,.!?：；:;\"\"''「」『』【】〔〕（）()[]{}、·")

DEFAULT_MIN_SEGMENT_DURATION = 1.8
DEFAULT_MAX_CHARS_PER_SENT = 30
MIN_CHARS_TO_BREAK = 3


def _clean(text: str) -> str:
    """去掉标点，只保留有效字符"""
    return "".join(c for c in text if c not in ALL_PUNCTUATION)


def segment_by_text(
    timestamps: list,
    min_duration: float = DEFAULT_MIN_SEGMENT_DURATION,
    audio_duration: float = None,
) -> list:
    """
    从字级时间戳自动生成视频分段。

    :param timestamps:     字级时间戳列表
    :param min_duration:   最短段落时长（秒）
    :param audio_duration: 音频总时长（秒），用于修正最后一段
    :return:               分段列表
    """
    if not timestamps:
        return []

    raw_sentences = _split_sentences(timestamps)
    logger.info("切句完成，共 %d 句", len(raw_sentences))

    merged = _merge_short_sentences(raw_sentences, min_duration)
    logger.info("合并后共 %d 段", len(merged))

    segments = []
    for s in merged:
        start = round(s["start"], 3)
        end = round(s["end"], 3)
        segments.append(
            {
                "start": start,
                "end": end,
                "duration": round(end - start, 3),
                "text": s["text"].strip(),
            }
        )

    if segments and audio_duration:
        segments[-1]["end"] = round(audio_duration, 3)
        segments[-1]["duration"] = round(
            audio_duration - segments[-1]["start"], 3
        )

    return segments


def _split_sentences(timestamps: list) -> list:
    """将字流按标点拆成句子"""
    sentences = []
    buf_words = []
    buf_start = None
    buf_end = None

    def flush():
        if not buf_words:
            return
        raw = "".join(w["word"] for w in buf_words)
        text = raw.rstrip("，,；;：:")
        if not _clean(text):
            return
        sentences.append(
            {"text": text, "start": buf_start, "end": buf_end}
        )

    for item in timestamps:
        word = item.get("word", "").strip()
        start_time = float(item.get("start_time", 0.0))
        end_time = float(item.get("end_time", 0.0))

        if not word:
            continue

        if buf_start is None:
            buf_start = start_time
        buf_end = end_time
        buf_words.append(
            {"word": word, "start": start_time, "end": end_time}
        )

        raw_text = "".join(w["word"] for w in buf_words)
        char_count = len(_clean(raw_text))
        last_char = word[-1] if word else ""
        is_end = last_char in END_PUNCTUATION
        is_mid = last_char in MID_PUNCTUATION
        is_max = char_count >= DEFAULT_MAX_CHARS_PER_SENT
        is_short = char_count < MIN_CHARS_TO_BREAK

        if is_end and not is_short:
            flush()
            buf_words = []
            buf_start = None
            buf_end = None
            continue

        if is_max:
            flush()
            buf_words = []
            buf_start = None
            buf_end = None

    flush()
    return sentences


def _merge_short_sentences(sentences: list, min_duration: float) -> list:
    """合并时长不足的句子"""
    if not sentences:
        return []

    merged = []
    buf = None

    for s in sentences:
        dur = s["end"] - s["start"]

        if buf is None:
            buf = {"text": s["text"], "start": s["start"], "end": s["end"]}
        else:
            buf["text"] += s["text"]
            buf["end"] = s["end"]

        buf_dur = buf["end"] - buf["start"]
        if buf_dur >= min_duration:
            merged.append(buf)
            buf = None

    if buf is not None:
        if merged:
            merged[-1]["text"] += buf["text"]
            merged[-1]["end"] = buf["end"]
        else:
            merged.append(buf)

    return merged
