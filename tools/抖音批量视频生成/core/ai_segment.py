"""
ai_segment.py - AI 智能分段模块
─────────────────────────────
使用豆包大模型对文案进行智能分段，适用于无时间戳场景。
"""

import json
from .config import config


class AISegmenter:
    """使用 AI 大模型进行视频文案智能分段"""

    def __init__(self):
        api_key = config.get("doubao_api_key")
        base_url = config.get(
            "doubao_base_url", "https://ark.cn-beijing.volces.com/api/coding/v3"
        )
        self.model = config.get("doubao_model")

        if api_key:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = None

    def segment(self, text, audio_duration, timestamps=None):
        """
        智能分段。

        :param text:           完整文案
        :param audio_duration: 音频总时长（秒）
        :param timestamps:     TTS 返回的时间戳列表（可选）
        :return:               分段结果数组
        """
        if self.client is None:
            raise RuntimeError(
                "AI 分段未配置，请在设置中填写豆包 API Key"
            )

        prompt = (
            f"你是一名专业的短视频分镜师。以下是一段口播文案及其音频总时长{audio_duration}秒。\n"
            f"请根据画面切换逻辑，将其拆分为若干片段，每个片段建议时长2~6秒，\n"
            f"并给出每个片段对应的开始时间、结束时间和文字内容。\n"
            f"输出严格使用JSON格式，不要其他内容，字段为：\n"
            f'[{{"start": 0.0, "end": 3.2, "text": "片段文字"}}]\n'
            f"\n文案内容：\n{text}\n"
        )

        result = ""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是专业的短视频分镜师，只返回JSON格式的分段结果，不要其他内容。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            result = response.choices[0].message.content.strip()

            if result.startswith("```"):
                lines = result.splitlines()
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                result = "\n".join(lines).strip()

            segments = json.loads(result)

            validated_segments = []
            total_time = 0.0
            for seg in segments:
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", 0.0))
                seg_text = seg.get("text", "").strip()
                if end > start and seg_text:
                    validated_segments.append(
                        {
                            "start": start,
                            "end": end,
                            "text": seg_text,
                            "duration": end - start,
                        }
                    )
                    total_time = max(total_time, end)

            if validated_segments and total_time < audio_duration:
                validated_segments[-1]["end"] = audio_duration
                validated_segments[-1]["duration"] = (
                    validated_segments[-1]["end"]
                    - validated_segments[-1]["start"]
                )

            if len(validated_segments) < 2:
                mid = audio_duration / 2
                validated_segments = [
                    {
                        "start": 0.0,
                        "end": mid,
                        "text": text[: len(text) // 2],
                        "duration": mid,
                    },
                    {
                        "start": mid,
                        "end": audio_duration,
                        "text": text[len(text) // 2 :],
                        "duration": audio_duration - mid,
                    },
                ]

            return validated_segments

        except json.JSONDecodeError as e:
            raise Exception(
                f"AI返回结果解析失败: {str(e)}，返回内容: {result}"
            )
        except Exception as e:
            raise Exception(f"AI分段失败: {str(e)}")
