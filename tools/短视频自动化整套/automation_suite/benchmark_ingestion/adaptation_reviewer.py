from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import re

import requests

logger = logging.getLogger("BenchmarkIngestion.AdaptationReviewer")


REVIEW_SYSTEM_PROMPT = """你是一位短视频对标文案的适配审查员。你的任务是保守过滤不适合进入后续批量生产链路的文案。

账号固定人设：
- 男性
- 男道士
- 男命理师
- 面向命理、玄学、修行相关短视频口播

审查原则：保守过滤，宁可拒绝，也不要让时效错位、身份错位、作者私货或女性视角进入后续流程。

重点识别风险：
1. 时效错位：清明节、春节、中元节、冬至、去年、2025 年、月份、生肖年等与当前日期不匹配的表达
2. 身份错位：女性视角、女性博主口吻、宝妈、姐妹们、老公、男朋友等不适合男道士/男命理师人设的表达
3. 作者自述：原作者本人经历、账号经历、门店、收徒、地域、客户案例等强绑定内容
4. 过往经历：讲述个人过去经历、人生故事、成长经历、从业经历、亲身遭遇、曾经如何如何等内容，默认 reject
5. 不可迁移内容：核心观点依赖原作者身份、经历或已过期事件，改写后容易显得虚假

决策规则：
- keep：没有明显风险，可以原样进入文案库
- rewrite：只有轻微可迁移问题，删除或替换少量人称/称呼后仍然忠实可用
- reject：存在明显时效错位、身份错位、作者自述、过往经历、女性视角、不可迁移经历，或你不确定是否安全

只输出 JSON，不要输出解释文本。格式如下：
{
  "decision": "keep | rewrite | reject",
  "reason": "一句话说明原因",
  "risk_tags": ["时效错位", "身份错位", "作者自述", "过往经历", "女性视角", "不可迁移经历"],
  "adapted_script": "keep 时可为空或原文；rewrite 时输出改写后的可用文案；reject 时必须为空"
}
"""


@dataclass
class AdaptationReviewResult:
    decision: str
    reason: str = ""
    risk_tags: list[str] = field(default_factory=list)
    adapted_script: str = ""


class ScriptAdaptationReviewer:
    """LLM-based content adaptation reviewer.

    Reviews ingested scripts against a fixed persona (male Taoist numerologist)
    and filters out content with persona mismatch, temporal issues, or
    non-transferable personal experiences.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "doubao-seed-2.0-pro",
        base_url: str = "https://ark.cn-beijing.volces.com/api/coding/v3",
        timeout: int = 90,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def review_text(self, text: str) -> AdaptationReviewResult:
        source = (text or "").strip()
        if not source:
            return reject_result("空文案，拒绝入库", ["empty_script"])

        today = datetime.now().strftime("%Y-%m-%d")
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"当前日期：{today}\n\n【待审查文案】\n{source}",
            },
        ]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            initial_max_tokens = max(2000, min(8000, len(source) * 4))
            token_budgets = [initial_max_tokens]
            if initial_max_tokens < 8000:
                token_budgets.append(8000)

            last_result = None
            for attempt, max_tokens in enumerate(token_budgets, start=1):
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                }
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    logger.error("适配审查 LLM 调用失败: HTTP %s, %s", response.status_code, response.text)
                    return reject_result("适配审查 LLM 调用失败，保守拒绝", ["review_failed"])

                choice = response.json().get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                finish_reason = str(choice.get("finish_reason", "")).lower()
                result = parse_review_result(content)
                last_result = result
                if result.risk_tags != ["review_failed"]:
                    return result

                can_retry = attempt < len(token_budgets) and (
                    finish_reason == "length" or not content.strip()
                )
                if not can_retry:
                    logger.warning(
                        "适配审查结果解析失败: finish_reason=%s, content_preview=%r",
                        finish_reason,
                        content[:500],
                    )
                    return result

                logger.warning(
                    "适配审查输出疑似被截断，准备使用更大 max_tokens 重试: finish_reason=%s, max_tokens=%s",
                    finish_reason,
                    max_tokens,
                )

            return last_result or reject_result("适配审查结果解析失败，保守拒绝", ["review_failed"])
        except Exception as exc:
            logger.error("适配审查 LLM 调用异常: %s", exc, exc_info=True)
            return reject_result("适配审查 LLM 调用异常，保守拒绝", ["review_failed"])


def parse_review_result(text: str) -> AdaptationReviewResult:
    try:
        payload = json.loads(strip_json_wrappers(text))
    except Exception:
        return reject_result("适配审查结果解析失败，保守拒绝", ["review_failed"])

    if not isinstance(payload, dict):
        return reject_result("适配审查结果不是 JSON 对象，保守拒绝", ["review_failed"])

    decision = str(payload.get("decision", "")).strip().lower()
    reason = str(payload.get("reason", "")).strip()
    risk_tags = payload.get("risk_tags", [])
    if not isinstance(risk_tags, list):
        risk_tags = [str(risk_tags).strip()] if risk_tags else []
    risk_tags = [str(tag).strip() for tag in risk_tags if str(tag).strip()]
    adapted_script = str(payload.get("adapted_script", "")).strip()

    if decision not in {"keep", "rewrite", "reject"}:
        return reject_result("适配审查 decision 无效，保守拒绝", ["review_failed"])
    if decision == "rewrite" and not adapted_script:
        return reject_result("适配审查要求改写但未返回文案，保守拒绝", ["review_failed"])
    if decision == "reject":
        adapted_script = ""

    return AdaptationReviewResult(
        decision=decision,
        reason=reason or "适配审查完成",
        risk_tags=risk_tags,
        adapted_script=adapted_script,
    )


def strip_json_wrappers(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def reject_result(reason: str, risk_tags: list[str] | None = None) -> AdaptationReviewResult:
    return AdaptationReviewResult(
        decision="reject",
        reason=reason,
        risk_tags=risk_tags or [],
        adapted_script="",
    )
