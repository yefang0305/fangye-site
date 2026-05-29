"""Douyin creator content cleanup helpers and browser automation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re
from collections.abc import Callable, Iterable


@dataclass(frozen=True)
class WorkInfo:
    title: str
    publish_time: datetime | None
    plays: int | None
    likes: int | None
    has_detail_link: bool


@dataclass(frozen=True)
class ParsedWork(WorkInfo):
    publish_time_text: str
    plays_text: str
    likes_text: str


@dataclass(frozen=True)
class CleanupDecision:
    should_delete: bool
    reason: str


@dataclass(frozen=True)
class CleanupResult:
    account_id: int
    account_name: str
    title: str
    publish_time: str
    plays: str
    likes: str
    reason: str
    status: str
    detail: str = ""


def parse_count(raw: str | None) -> int | None:
    if raw is None:
        return None
    text = raw.strip().replace(",", "")
    if not text or text == "-":
        return None
    multiplier = 1
    if text.endswith("万"):
        multiplier = 10000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return None


def parse_publish_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    for fmt in ("%Y年%m月%d日 %H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_work_from_row_text(text: str) -> ParsedWork:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = ""
    publish_time_text = ""
    plays_text = ""
    likes_text = ""

    time_re = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2}")
    duration_re = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
    ignored_title_lines = {
        "播放",
        "点赞",
        "评论",
        "分享",
        "删除作品",
        "查看详情",
        "编辑作品",
        "作品置顶",
        "设置权限",
    }
    for index, line in enumerate(lines):
        if not title and line not in ignored_title_lines and not duration_re.match(line):
            if not time_re.search(line):
                title = line
        if not publish_time_text:
            match = time_re.search(line)
            if match:
                publish_time_text = match.group(0)
        if line == "播放" and index + 1 < len(lines):
            plays_text = lines[index + 1]
        if line == "点赞" and index + 1 < len(lines):
            likes_text = lines[index + 1]

    return ParsedWork(
        title=title,
        publish_time=parse_publish_time(publish_time_text),
        publish_time_text=publish_time_text,
        plays=parse_count(plays_text),
        plays_text=plays_text,
        likes=parse_count(likes_text),
        likes_text=likes_text,
        has_detail_link="查看详情" in text,
    )


def choose_cleanup_action(work: WorkInfo, now: datetime | None = None) -> CleanupDecision:
    now = now or datetime.now()
    if work.has_detail_link:
        return CleanupDecision(True, "限流查看详情")

    if work.publish_time is None:
        return CleanupDecision(False, "发布时间缺失跳过")
    if now - work.publish_time < timedelta(hours=24):
        return CleanupDecision(False, "24小时内跳过")

    if work.plays is None or work.likes is None:
        return CleanupDecision(False, "指标缺失跳过")
    if work.plays < 1000 and work.likes < 30:
        return CleanupDecision(True, "低播放低点赞")
    return CleanupDecision(False, "数据达标跳过")


def matches_retry_target(work: WorkInfo, target_title: str = "", target_publish_time: str = "") -> bool:
    title = (target_title or "").strip()
    publish_time = (target_publish_time or "").strip()
    if not title and not publish_time:
        return True
    if title and work.title.strip() != title:
        return False
    if publish_time:
        expected = parse_publish_time(publish_time)
        if expected is None or work.publish_time != expected:
            return False
    return True


def is_active_douyin_account(account: dict) -> bool:
    return account.get("platform") == "douyin" and int(account.get("is_active") or 0) == 1


DOUYIN_CONTENT_MANAGE_URL = "https://creator.douyin.com/creator-micro/content/manage"
LOGIN_URL_MARKERS = ("/login", "/passport")
NAV_TIMEOUT_MS = 30_000
ROW_WAIT_MS = 20_000
STEP_TIMEOUT_MS = 8_000

CONFIRM_DELETE_SELECTORS = [
    ".semi-modal button:has-text('确定')",
    ".semi-modal button:has-text('确认')",
    "[role='dialog'] button:has-text('确定')",
    "[role='dialog'] button:has-text('确认')",
    "button:has-text('确定')",
    "button:has-text('确认')",
]

BLOCKING_SELECTORS = [
    "text=验证码",
    "text=安全验证",
    "text=身份验证",
    "text=请完成验证",
    "text=登录",
]


def _logs_dir() -> Path:
    base = Path(__file__).resolve().parent.parent / "logs"
    base.mkdir(exist_ok=True)
    return base


def _shoot(page, step: str) -> str:
    try:
        out = _logs_dir() / f"douyin-cleanup-{step}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        page.screenshot(path=str(out), full_page=True)
        return str(out)
    except Exception:
        return ""


def _first_visible(page, selectors: list[str], timeout_ms: int = 300):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout_ms)
            return loc
        except Exception:
            continue
    return None


def _blocking_reason(page) -> str:
    if any(marker in page.url for marker in LOGIN_URL_MARKERS):
        return f"账号登录失效: {page.url}"
    loc = _first_visible(page, BLOCKING_SELECTORS, timeout_ms=200)
    if loc is None:
        return ""
    try:
        text = loc.inner_text(timeout=500).strip()
    except Exception:
        text = "页面出现验证/登录提示"
    return text or "页面出现验证/登录提示"


def _confirm_delete_dialog(page) -> None:
    loc = _first_visible(page, CONFIRM_DELETE_SELECTORS, timeout_ms=1500)
    if loc is not None:
        loc.click(timeout=STEP_TIMEOUT_MS)


class DouyinCleanupRunner:
    def __init__(
        self,
        accounts: Iterable[dict],
        clean_account: Callable[[dict, Callable[[], bool]], Iterable[CleanupResult]] | None = None,
        stop_requested: Callable[[], bool] | None = None,
    ):
        self._accounts = list(accounts)
        self._clean_account = clean_account or self._default_clean_account
        self._stop_requested = stop_requested or (lambda: False)

    def run(self) -> Iterable[CleanupResult]:
        for account in self._accounts:
            if self._stop_requested():
                break
            if not is_active_douyin_account(account):
                continue
            yield from self._clean_account(account, self._stop_requested)

    @staticmethod
    def _default_clean_account(account: dict, stop_requested: Callable[[], bool]) -> Iterable[CleanupResult]:
        return DouyinWorkCleaner().clean_account(account, stop_requested=stop_requested)


class DouyinWorkCleaner:
    def clean_account(
        self,
        account: dict,
        stop_requested: Callable[[], bool] | None = None,
        limit: int = 30,
        target_title: str = "",
        target_publish_time: str = "",
    ) -> list[CleanupResult]:
        from playwright.sync_api import sync_playwright

        stop_requested = stop_requested or (lambda: False)
        account_id = int(account.get("id") or 0)
        account_name = str(account.get("display_name") or account_id)
        profile_path = str(account.get("profile_path") or "")
        if not profile_path:
            return [
                CleanupResult(
                    account_id=account_id,
                    account_name=account_name,
                    title="",
                    publish_time="",
                    plays="",
                    likes="",
                    reason="账号配置缺失",
                    status="失败",
                    detail="这个账号没有本地浏览器 Profile 路径",
                )
            ]

        results: list[CleanupResult] = []
        processed: set[str] = set()

        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=Path(profile_path).as_posix(),
                    headless=False,
                    viewport={"width": 1280, "height": 900},
                )
                try:
                    page = ctx.new_page() if not ctx.pages else ctx.pages[0]
                    page.set_default_timeout(STEP_TIMEOUT_MS)
                    page.goto(DOUYIN_CONTENT_MANAGE_URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                    page.wait_for_timeout(1500)

                    reason = _blocking_reason(page)
                    if reason:
                        shot = _shoot(page, f"blocked-{account_id}")
                        return [
                            CleanupResult(account_id, account_name, "", "", "", "", reason, "失败", shot)
                        ]

                    page.locator("text=删除作品").first.wait_for(state="visible", timeout=ROW_WAIT_MS)
                    stagnant_passes = 0
                    while len(processed) < limit and not stop_requested():
                        deleted_this_pass = False
                        found_new = False
                        delete_buttons = page.locator("text=删除作品")
                        count = min(delete_buttons.count(), max(0, limit - len(processed)))
                        for index in range(count):
                            if stop_requested() or len(processed) >= limit:
                                break
                            delete_button = delete_buttons.nth(index)
                            row = self._row_for_delete_button(delete_button)
                            row_text = row.inner_text(timeout=STEP_TIMEOUT_MS)
                            work = parse_work_from_row_text(row_text)
                            if not matches_retry_target(work, target_title, target_publish_time):
                                continue
                            key = f"{work.title}|{work.publish_time_text}"
                            if not key.strip("|") or key in processed:
                                continue
                            processed.add(key)
                            found_new = True

                            decision = choose_cleanup_action(work)
                            if not decision.should_delete:
                                results.append(
                                    self._result(account_id, account_name, work, decision.reason, "跳过")
                                )
                                continue

                            try:
                                delete_button.click(timeout=STEP_TIMEOUT_MS)
                                _confirm_delete_dialog(page)
                                page.wait_for_timeout(1800)
                                results.append(
                                    self._result(account_id, account_name, work, decision.reason, "已删除")
                                )
                                deleted_this_pass = True
                                break
                            except Exception as exc:
                                shot = _shoot(page, f"delete-failed-{account_id}")
                                results.append(
                                    self._result(
                                        account_id,
                                        account_name,
                                        work,
                                        decision.reason,
                                        "失败",
                                        f"{type(exc).__name__}: {exc}; screenshot={shot}",
                                    )
                                )

                        if deleted_this_pass:
                            stagnant_passes = 0
                            continue
                        if len(processed) >= limit:
                            break
                        if not found_new:
                            stagnant_passes += 1
                        else:
                            stagnant_passes = 0
                        if stagnant_passes >= 2:
                            break
                        page.mouse.wheel(0, 900)
                        page.wait_for_timeout(1000)
                    if target_title or target_publish_time:
                        matched = any(
                            r.title == target_title and (not target_publish_time or r.publish_time == target_publish_time)
                            for r in results
                        )
                        if not matched:
                            results.append(
                                CleanupResult(
                                    account_id=account_id,
                                    account_name=account_name,
                                    title=target_title,
                                    publish_time=target_publish_time,
                                    plays="",
                                    likes="",
                                    reason="重试失败",
                                    status="失败",
                                    detail="未在作品管理页找到原作品",
                                )
                            )
                finally:
                    ctx.close()
        except Exception as exc:
            results.append(
                CleanupResult(
                    account_id=account_id,
                    account_name=account_name,
                    title="",
                    publish_time="",
                    plays="",
                    likes="",
                    reason="账号清理失败",
                    status="失败",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
        return results

    @staticmethod
    def _row_for_delete_button(delete_button):
        return delete_button.locator(
            "xpath=ancestor::div[contains(., '播放') and contains(., '点赞')][1]"
        )

    @staticmethod
    def _result(
        account_id: int,
        account_name: str,
        work: ParsedWork,
        reason: str,
        status: str,
        detail: str = "",
    ) -> CleanupResult:
        return CleanupResult(
            account_id=account_id,
            account_name=account_name,
            title=work.title,
            publish_time=work.publish_time_text,
            plays=work.plays_text,
            likes=work.likes_text,
            reason=reason,
            status=status,
            detail=detail,
        )
