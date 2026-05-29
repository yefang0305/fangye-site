"""
subtitle.py - ASS 字幕生成模块
─────────────────────────────
基于 TTS 字级时间戳生成 ASS 字幕文件。
"""

from pathlib import Path
from .config import config

MAX_CHARS_PER_LINE = 15
MAX_CHARS_LANDSCAPE = 28
MIN_CHARS_PER_LINE = 3
DEFAULT_SUBTITLE_OFFSET_SEC = 0.15

SPLIT_PUNCTUATION = set("。！？；，、…!?,;")
ALL_PUNCTUATION = set("。！？…，,.!?：；:;\"\"''「」『』【】〔〕（）()[]{}、·")


class SubtitleGenerator:
    """ASS 字幕生成器"""

    def __init__(self, resolution="1080x1920"):
        self.resolution = resolution
        width, height = map(int, resolution.split("x"))
        self.width = width
        self.height = height
        self.is_landscape = self.width > self.height

    def generate_from_timestamps(
        self, timestamps: list, output_path: str, max_chars: int = 0
    ) -> str:
        """
        从字级时间戳生成 ASS 字幕文件。
        """
        if not timestamps:
            raise ValueError("时间戳数据为空，无法生成字幕")

        if not max_chars:
            max_chars = self._effective_max_chars()

        sentences = self._merge_into_sentences(timestamps, max_chars)
        ass_content = self._build_ass(sentences)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ass_content, encoding="utf-8-sig")
        return str(output_path)

    def generate_from_segments(
        self, segments: list, audio_duration: float, output_path: str
    ) -> str:
        """
        兜底方案：无时间戳时，用手动分段数据生成字幕。
        """
        remove_punctuation = config.get("subtitle_remove_punctuation", False)
        max_chars = self._effective_max_chars()

        def clean(text: str) -> str:
            text = text.rstrip("，,；;、：:。！？…")
            if remove_punctuation:
                return "".join(c for c in text if c not in ALL_PUNCTUATION)
            return text

        sentences = []
        offset = config.get("subtitle_offset_sec", DEFAULT_SUBTITLE_OFFSET_SEC)
        for seg in segments:
            text = clean(seg.get("text", "").strip())
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", audio_duration))
            if not text:
                continue
            chunks = self._split_evenly(text, max_chars)
            duration = (end - start) / len(chunks)
            for i, chunk in enumerate(chunks):
                seg_start = round(start + i * duration, 3)
                seg_end = round(start + (i + 1) * duration, 3)
                seg_start = max(0.0, seg_start - offset)
                seg_end = max(seg_start + 0.1, seg_end)
                sentences.append(
                    {"text": chunk, "start": seg_start, "end": seg_end}
                )

        ass_content = self._build_ass(sentences)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ass_content, encoding="utf-8-sig")
        return str(output_path)

    def _merge_into_sentences(
        self, timestamps: list, max_chars: int
    ) -> list:
        """核心分句逻辑"""
        remove_punctuation = config.get("subtitle_remove_punctuation", False)

        def clean(text: str) -> str:
            text = text.rstrip("，,；;、：:。！？…")
            if remove_punctuation:
                return "".join(c for c in text if c not in ALL_PUNCTUATION)
            return text

        # 步骤一：按标点切断
        raw_segs = []
        buf_words = []
        buf_start = None
        buf_end = None

        for item in timestamps:
            word = item.get("word", "").strip()
            if not word:
                continue
            start_time = float(item.get("start_time", 0.0))
            end_time = float(item.get("end_time", 0.0))

            if buf_start is None:
                buf_start = start_time
            buf_end = end_time
            buf_words.append(item)

            if word[-1] in SPLIT_PUNCTUATION:
                text = clean("".join(w["word"] for w in buf_words))
                if text:
                    raw_segs.append(
                        {"text": text, "start": buf_start, "end": buf_end}
                    )
                buf_words = []
                buf_start = buf_end = None

        if buf_words:
            text = clean("".join(w["word"] for w in buf_words))
            if text:
                raw_segs.append(
                    {"text": text, "start": buf_start, "end": buf_end}
                )

        if not raw_segs:
            return []

        # 步骤二：短片段向后合并
        i = 0
        while i < len(raw_segs) - 1:
            cur = raw_segs[i]
            nxt = raw_segs[i + 1]
            if len(cur["text"]) < MIN_CHARS_PER_LINE:
                combined = cur["text"] + nxt["text"]
                if len(combined) <= max_chars:
                    raw_segs[i + 1] = {
                        "text": combined,
                        "start": cur["start"],
                        "end": nxt["end"],
                    }
                    raw_segs.pop(i)
                    continue
            i += 1

        # 末尾段向前合并
        if len(raw_segs) > 1 and len(raw_segs[-1]["text"]) < MIN_CHARS_PER_LINE:
            last = raw_segs.pop()
            prev = raw_segs[-1]
            combined = prev["text"] + last["text"]
            if len(combined) <= max_chars:
                raw_segs[-1] = {
                    "text": combined,
                    "start": prev["start"],
                    "end": last["end"],
                }
            else:
                raw_segs.append(last)

        # 步骤三：构建 sentences
        sentences = []
        for seg in raw_segs:
            sentences.append(
                {
                    "text": seg["text"],
                    "start": round(seg["start"], 3),
                    "end": round(seg["end"], 3),
                }
            )

        # 步骤四：偏移修正 + 防重叠 + 间隙填充
        offset = config.get("subtitle_offset_sec", DEFAULT_SUBTITLE_OFFSET_SEC)
        for s in sentences:
            s["start"] = max(0.0, s["start"] - offset)
            s["end"] = max(s["start"] + 0.1, s["end"])

        for i in range(len(sentences) - 1):
            cur_end = sentences[i]["end"]
            next_start = sentences[i + 1]["start"]
            if cur_end > next_start:
                sentences[i]["end"] = next_start
            elif next_start - cur_end > 0.1:
                sentences[i]["end"] = next_start - 0.05

        return sentences

    def _effective_max_chars(self) -> int:
        """决定单行最大字数"""
        user_val = config.get("subtitle_max_chars", 0)
        if user_val and user_val > 0:
            return int(user_val)

        font_size = config.get("subtitle_font_size", 52)
        if font_size and font_size > 0 and self.width > 0:
            return max(6, int(self.width * 0.88 / font_size * 0.88))

        return MAX_CHARS_LANDSCAPE if self.is_landscape else MAX_CHARS_PER_LINE

    def _get_ass_style(self) -> str:
        """从配置读取 ASS 样式头"""
        font_name = config.get("subtitle_font", "Microsoft YaHei")
        font_size = config.get("subtitle_font_size", 52)
        font_color = config.get("subtitle_color", "&H00FFFFFF")
        outline_color = config.get("subtitle_outline_color", "&H00000000")
        outline_size = (
            config.get("subtitle_outline_size", 2)
            if config.get("subtitle_outline", True)
            else 0
        )
        shadow_offset = (
            config.get("subtitle_shadow_offset", 2)
            if config.get("subtitle_shadow", True)
            else 0
        )
        shadow_type = 1 if shadow_offset > 0 else 0

        position_y_pct = config.get("subtitle_position_y", 80)
        margin_v = int(self.height * (100 - position_y_pct) / 100)

        return (
            f"[Script Info]\n"
            f"ScriptType: v4.00+\n"
            f"PlayResX: {self.width}\n"
            f"PlayResY: {self.height}\n"
            f"ScaledBorderAndShadow: yes\n"
            f"WrapStyle: 2\n"
            f"\n"
            f"[V4+ Styles]\n"
            f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            f"OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            f"ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            f"Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{font_name},{font_size},{font_color},&H000000FF,"
            f"{outline_color},&H00000000,-1,0,0,0,100,100,0,0,1,"
            f"{outline_size},{shadow_type},2,10,10,{margin_v},1\n"
            f"\n"
            f"[Events]\n"
            f"Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

    def _build_ass(self, sentences: list) -> str:
        """将句子列表渲染为 ASS 字幕文本"""
        max_chars = self._effective_max_chars()
        lines = [self._get_ass_style()]
        for s in sentences:
            start = SubtitleGenerator._sec_to_ass(s["start"])
            end = SubtitleGenerator._sec_to_ass(s["end"])
            text = s["text"].replace("\n", "").replace("\\N", "")
            if len(text) > max_chars:
                text = self._wrap_to_two_lines(text, max_chars)
            lines.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _wrap_to_two_lines(text: str, max_chars: int) -> str:
        """将超长文本折成两行"""
        if "\\N" in text:
            return text
        n = len(text)
        mid = n // 2
        BREAK_CHARS = set("，,、；;：:")
        best = -1
        for radius in range(mid):
            for pos in (mid - radius, mid + radius):
                if 0 < pos < n and text[pos - 1] in BREAK_CHARS:
                    best = pos
                    break
            if best != -1:
                break
        if best == -1:
            best = mid
        return text[:best] + "\\N" + text[best:]

    @staticmethod
    def _split_evenly(text: str, max_chars: int) -> list:
        """将长文本按最大字数等分"""
        if len(text) <= max_chars:
            return [text]
        chunks = []
        while text:
            chunks.append(text[:max_chars])
            text = text[max_chars:]
        return chunks

    @staticmethod
    def _sec_to_ass(sec: float) -> str:
        """秒数转 ASS 时间格式 H:MM:SS.cc"""
        sec = max(0.0, sec)
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int(round((sec % 1) * 100))
        if cs >= 100:
            cs = 0
            s += 1
            if s >= 60:
                s = 0
                m += 1
                if m >= 60:
                    m = 0
                    h += 1
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
