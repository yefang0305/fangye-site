from __future__ import annotations

import logging
import re
import time

import requests

logger = logging.getLogger("BenchmarkIngestion.LLMCleaner")


SYSTEM_PROMPT = """你是一位短视频 ASR 口播文案校对员。你的任务是把语音识别出来的原始口播稿清洗成可复用的源文案。

【只允许做】
1. 根据上下文纠正明显的 ASR 错字、同音字、漏字、多字
2. 补全标点符号，按语义断句和分段
3. 清理明显重复识别的句子或词组
4. 保留原口播的人称、语气、口语化表达和信息顺序

【禁止做】
1. 不要改写成新文案
2. 不要扩写、总结、提炼、升华或增加观点
3. 不要加入标题、标签、说明、分析或项目符号
4. 不要改变原文立场、风格和表达意图

直接输出清洗后的纯文案。"""


class ASRCleaningLLMClient:
    """LLM-based ASR transcript cleaner using OpenAI-compatible API.

    Uses an LLM to fix ASR errors while preserving the original speaking style.
    Configured for doubao-seed-2.0-pro via 火山引擎 by default.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "doubao-seed-2.0-pro",
        base_url: str = "https://ark.cn-beijing.volces.com/api/coding/v3",
        timeout: int = 180,
        max_retries: int = 1,
        retry_delay: float = 1.5,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_delay = max(0.0, retry_delay)

    def optimize_text(self, text: str) -> str | None:
        source = (text or "").strip()
        if not source:
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"【ASR 原始口播稿】\n{source}"},
            ],
            "temperature": 0.2,
            "max_tokens": max(1200, min(8000, len(source) * 3)),
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    logger.error("ASR 清洗 LLM 调用失败: HTTP %s, %s", response.status_code, response.text)
                    return None
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                cleaned = strip_llm_wrappers(content)
                return cleaned or None
            except requests.exceptions.Timeout as exc:
                if attempt >= self.max_retries:
                    logger.error("ASR 清洗 LLM 调用超时: %s", exc, exc_info=True)
                    return None
                logger.warning("ASR 清洗 LLM 调用超时，准备重试 %s/%s", attempt + 1, self.max_retries)
                if self.retry_delay:
                    time.sleep(self.retry_delay)
            except Exception as exc:
                logger.error("ASR 清洗 LLM 调用异常: %s", exc, exc_info=True)
                return None
        return None


def strip_llm_wrappers(text: str) -> str:
    """Strip markdown code fences and prefix labels from LLM output."""
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:text|txt|markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(r"^\s*(清洗后文案|优化后文案|校对后文案)[:：]\s*", "", cleaned)
    return cleaned.strip()
