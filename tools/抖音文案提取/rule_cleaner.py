from __future__ import annotations

ASR_CORRECTIONS = [
    ("看挂", "看卦"),
    ("看卦子", "看卦"),
    ("借色", "戒色"),
    ("甚虚", "肾虚"),
    ("甚好的人", "肾好的人"),
    ("甚好", "肾好"),
    ("精满不思音", "精满不思淫"),
    ("气满不思时", "气满不思食"),
    ("精化器", "精化气"),
    ("面红耳深", "面红耳赤"),
    ("死语", "私欲"),
    ("地狱下", "地狱相"),
    ("奶头乐", "奶嘴乐"),
    ("音符经", "阴符经"),
    ("重彩票", "中彩票"),
    ("道德底下", "道德底线"),
    ("的食候", "的时候"),
    ("这个食候", "这个时候"),
    ("那个食候", "那个时候"),
    ("有食候", "有时候"),
    ("食间", "时间"),
    ("食代", "时代"),
]

FULL_LINE_FILLERS = {"嗯", "啊", "对吧", "是吧", "你知道吗", "明白吗"}
LINE_START_FILLERS = ("然后呢", "然后", "咱先说", "咱可以先", "我告诉你", "就是说", "嗯", "啊")
SALES_KEYWORDS = ("下单", "购买", "链接", "小黄车", "橱窗", "商品", "价格", "优惠", "限时", "秒杀", "点击")


def clean_transcript_rules(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines and text.strip():
        lines = [text.strip()]
    if _is_sales_content(lines):
        return ""
    lines = _correct(lines)
    processed = []
    for line in lines:
        line = _remove_filler(line)
        if line:
            processed.append(_add_punctuation(line))
    return "\n\n".join(_create_paragraphs(processed)).strip()


def _correct(lines: list[str]) -> list[str]:
    text = "\n".join(lines)
    for wrong, right in ASR_CORRECTIONS:
        text = text.replace(wrong, right)
    return text.splitlines()


def _remove_filler(line: str) -> str:
    line = line.strip()
    if line in FULL_LINE_FILLERS:
        return ""
    for filler in LINE_START_FILLERS:
        if line.startswith(filler):
            line = line[len(filler):].strip()
            if line.startswith(("，", "。", "！", "？")):
                line = line[1:].strip()
            break
    return line


def _add_punctuation(line: str) -> str:
    if not line or line[-1] in "。！？：；":
        return line
    if line.endswith(("吗", "呢", "啥")):
        return line + "？"
    return line + "。"


def _create_paragraphs(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    break_words = ("第一", "第二", "第三", "首先", "其次", "最后", "那么", "所以", "但是", "因为", "因此", "其实", "为什么", "怎么")
    for line in lines:
        should_break = current and (line.startswith(break_words) or len(current) >= 5)
        if should_break:
            paragraphs.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        paragraphs.append("".join(current))
    return paragraphs


def _is_sales_content(lines: list[str]) -> bool:
    count = 0
    for line in lines:
        count += sum(1 for keyword in SALES_KEYWORDS if keyword in line)
    return count >= 3
