"""Douyin (creator.douyin.com) Publisher.

Flow: open creator upload page → set video file → wait for the upload
form to appear → set title → optionally set scheduled time → click publish →
wait for the upload task window on the content list to finish.

Cover is intentionally NOT set: Douyin auto-uses the first frame, and
explicitly setting it would pop a cover-picker modal we'd then have to
dismiss. If the user later wants a different cover, do it once via
`extract_first_frame` + a strategy in `_set_cover` (kept in git history).

Each step has its own short timeout, multiple selector fallbacks, and
saves a screenshot to `logs/` on failure so we can diagnose UI changes.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from publisher.base import Publisher


# ---- URLs ----
URL_HOME = "https://creator.douyin.com/creator-micro/home"
URL_LOGIN = URL_HOME
URL_UPLOAD = "https://creator.douyin.com/creator-micro/content/upload"
URL_CONTENT_MANAGE = "https://creator.douyin.com/creator-micro/content/manage"

# ---- Selectors (Douyin updates HTML occasionally; fallbacks improve survival) ----

# Video file input (the first hidden input that accepts video MIME)
SEL_VIDEO_FILE_INPUT = "input[type='file'][accept*='video'], input[type='file'][accept*='mp4'], input[type='file']"

# Title input candidates — try in order, first match wins
SEL_TITLE_CANDIDATES = [
    "input[placeholder*='填写作品标题']",
    "input[placeholder*='标题']",
    "div[contenteditable='true'][data-placeholder*='标题']",
    "div[contenteditable='true'][placeholder*='标题']",
    "div.zone-container input.semi-input",  # observed in some skins
]

# After upload completes, the form area appears. Use any of these to detect "form ready".
SEL_FORM_READY_CANDIDATES = SEL_TITLE_CANDIDATES + [
    "text=作品标题",
    "text=填写作品标题",
]

# Upload/processing state. Douyin can show the title/scheduling form before the
# video file is actually ready, so form-ready alone is not enough.
SEL_UPLOAD_BUSY_CANDIDATES = [
    "text=上传中",
    "text=正在上传",
    "text=视频上传中",
    "text=上传视频中",
    "text=上传进度",
    "text=上传任务",
    "text=上传列表",
    "text=上传队列",
    "text=正在发布",
    "text=处理中",
    "text=正在处理",
    "text=转码中",
    "text=等待上传",
]
SEL_UPLOAD_DONE_CANDIDATES = [
    "text=上传成功",
    "text=视频上传成功",
    "text=上传完成",
    "text=发布完成",
    "text=处理完成",
]

# Scheduled mode
SEL_RADIO_SCHEDULED_CANDIDATES = [
    "label:has-text('定时发布')",
    "text=定时发布",
]
SEL_DATETIME_INPUT_CANDIDATES = [
    "input[placeholder*='发布时间']",
    "input[placeholder*='日期']",
    ".semi-datepicker input",
]

# Optional self-declaration field. Some videos trigger this required field
# before scheduling/publishing. Choose the neutral declaration so the workflow
# can continue.
SEL_SELF_DECLARATION_TRIGGER_CANDIDATES = [
    "text=请选择自主声明",
    "text=选择自主声明",
    "text=添加声明",
]
SEL_SELF_DECLARATION_OPTION_CANDIDATES = [
    "label:has-text('无需添加自主声明')",
    "text=无需添加自主声明",
]
SEL_SELF_DECLARATION_CONFIRM_CANDIDATES = [
    ".semi-modal button:has-text('确定')",
    "[role='dialog'] button:has-text('确定')",
    "button:has-text('确定')",
]

# Final publish button
SEL_PUBLISH_BUTTON_CANDIDATES = [
    "button.button-dhlUZE.primary-cECiOJ:has-text('发布')",  # observed CSS-modules class
    "button:has-text('发布'):not(:has-text('定时'))",
    "button.primary:has-text('发布')",
    "button:has-text('发布')",
]

# Success indicator — Douyin shows different things; try several
SEL_SUCCESS_CANDIDATES = [
    "text=发布成功",
    "text=作品发布成功",
    "text=作品提交成功",
    "text=已加入定时发布",
    "text=定时发布成功",
]

# Blocking indicators shown after the final submit click. These mean the video
# was not accepted into Douyin's publish/schedule queue yet, even if the page
# contains generic "success" CSS classes elsewhere.
SEL_BLOCKING_CANDIDATES = [
    "text=二次验证",
    "text=身份验证",
    "text=安全验证",
    "text=扫码验证",
    "text=验证码",
    "text=请完成验证",
    "text=操作频繁",
    "text=发布失败",
    "text=提交失败",
    "text=上传失败",
    "text=处理失败",
]

# Login markers
LOGIN_URL_MARKERS = ("/login", "/passport")

# Name selectors on creator home
NAME_SELECTORS = [
    "div.name-_lSSDc",
    "div[class*='name'] >> nth=0",
    "span.unique_id-EuH8eA",
]

# Timeouts (ms / s)
NAV_TIMEOUT_MS = 30_000
LOGIN_DETECT_WAIT_MS = 2_500
FORM_READY_TIMEOUT_MS = 8 * 60 * 1000   # video upload may take a while
STEP_TIMEOUT_MS = 30_000                # any single click/fill
SUCCESS_TIMEOUT_MS = 8 * 60 * 1000      # post-submit upload task can keep running on list page


def _logs_dir() -> Path:
    base = Path(__file__).resolve().parent.parent / "logs"
    base.mkdir(exist_ok=True)
    return base


def _shoot(page, step: str) -> str:
    """Save a debug screenshot. Returns absolute path or empty string on failure."""
    try:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = _logs_dir() / f"douyin-{step}-{ts}.png"
        page.screenshot(path=str(out), full_page=True)
        return str(out)
    except Exception:
        return ""


def _try_locators(page, selectors: list[str], timeout_ms: int = STEP_TIMEOUT_MS):
    """Return the first locator whose first element becomes visible within
    timeout. Raises the last error if none match."""
    last_err: Optional[Exception] = None
    per = max(1500, timeout_ms // max(1, len(selectors)))
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=per)
            return loc, sel
        except Exception as e:
            last_err = e
            continue
    raise TimeoutError(f"none of selectors visible: {selectors[:3]}... ({last_err})")


def _first_visible(page, selectors: list[str], timeout_ms: int = 500):
    """Return (locator, selector) for a currently visible selector, or None."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout_ms)
            return loc, sel
        except Exception:
            continue
    return None


def _submit_blocking_reason(page) -> str:
    for frame in page.frames:
        url = frame.url or ""
        if "second_verification" in url or "gateway_biz_verify" in url:
            return f"Douyin secondary verification required: {url}"

    match = _first_visible(page, SEL_BLOCKING_CANDIDATES, timeout_ms=250)
    if not match:
        return ""
    loc, sel = match
    try:
        text = loc.inner_text(timeout=500).strip()
    except Exception:
        text = sel
    return f"Douyin submit blocked by page indicator: {text or sel}"


def _is_content_manage_page(page) -> bool:
    try:
        return "/creator-micro/content/manage" in (page.url or "")
    except Exception:
        return False


def _wait_for_submit_result(page) -> tuple[bool, str]:
    deadline = time.time() + SUCCESS_TIMEOUT_MS / 1000
    last_err: Optional[Exception] = None
    saw_post_submit_upload = False
    stable_since: float | None = None
    content_manage_since: float | None = None

    while time.time() < deadline:
        reason = _submit_blocking_reason(page)
        if reason:
            return False, reason

        if _any_visible(page, SEL_UPLOAD_BUSY_CANDIDATES):
            saw_post_submit_upload = True
            stable_since = None
            content_manage_since = None
            page.wait_for_timeout(1000)
            continue

        try:
            _try_locators(page, SEL_SUCCESS_CANDIDATES, timeout_ms=3000)
            if not _any_visible(page, SEL_UPLOAD_BUSY_CANDIDATES):
                return True, ""
        except Exception as e:
            last_err = e

        if _is_content_manage_page(page):
            # Some successful submits return directly to the works list without
            # a visible toast or upload task window. If the list page is stable
            # and no blocking/busy indicator appears, close the browser and let
            # the queue record success.
            if content_manage_since is None:
                content_manage_since = time.time()
            if time.time() - content_manage_since >= 5:
                return True, ""
            page.wait_for_timeout(1000)
            continue
        content_manage_since = None

        if saw_post_submit_upload:
            # Douyin can return to the content list immediately and continue
            # uploading in a floating task window. Once that task window is no
            # longer visible and no failure indicator appeared, treat it as
            # accepted by the platform queue.
            if stable_since is None:
                stable_since = time.time()
            if time.time() - stable_since >= 5:
                return True, ""
            page.wait_for_timeout(1000)
            continue

        try:
            page.wait_for_timeout(1000)
        except Exception as e:
            last_err = e
            break

    return False, f"no final publish completion after post-submit upload: {last_err}"


def _any_visible(page, selectors: list[str], timeout_ms: int = 150) -> bool:
    return _first_visible(page, selectors, timeout_ms=timeout_ms) is not None


def _click_enabled(locator, timeout_ms: int = STEP_TIMEOUT_MS) -> None:
    deadline = time.time() + timeout_ms / 1000
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            if locator.is_enabled(timeout=500):
                locator.click()
                return
        except Exception as e:
            last_err = e
        time.sleep(0.2)
    raise TimeoutError(f"locator did not become enabled: {last_err}")


def _handle_self_declaration(page) -> bool:
    """Select '无需添加自主声明' when Douyin asks for content declaration.

    Returns True if the field/modal was handled, False when the page does not
    require a declaration for this upload.
    """
    trigger = _first_visible(page, SEL_SELF_DECLARATION_TRIGGER_CANDIDATES, timeout_ms=800)
    if not trigger:
        return False

    trigger_loc, _sel = trigger
    trigger_loc.click()

    option_loc, _sel = _try_locators(
        page,
        SEL_SELF_DECLARATION_OPTION_CANDIDATES,
        timeout_ms=STEP_TIMEOUT_MS,
    )
    option_loc.click()

    confirm_loc, _sel = _try_locators(
        page,
        SEL_SELF_DECLARATION_CONFIRM_CANDIDATES,
        timeout_ms=STEP_TIMEOUT_MS,
    )
    _click_enabled(confirm_loc)
    page.wait_for_timeout(500)
    return True


class DouyinPublisher(Publisher):
    platform = "douyin"
    display_name = "抖音"
    login_url = URL_LOGIN
    creator_home_url = URL_HOME
    login_url_markers = LOGIN_URL_MARKERS

    # ---- login / name ----
    def check_login(self, profile_path: str) -> bool:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(profile_path).as_posix()
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(user_data_dir, headless=True)
                try:
                    page = ctx.new_page() if not ctx.pages else ctx.pages[0]
                    page.goto(URL_HOME, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                    page.wait_for_timeout(LOGIN_DETECT_WAIT_MS)
                    return not any(m in page.url for m in LOGIN_URL_MARKERS)
                finally:
                    ctx.close()
        except Exception:
            return False

    def detect_account_name(self, profile_path: str) -> str:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(profile_path).as_posix()
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(user_data_dir, headless=True)
                try:
                    page = ctx.new_page() if not ctx.pages else ctx.pages[0]
                    page.goto(URL_HOME, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                    page.wait_for_timeout(LOGIN_DETECT_WAIT_MS)
                    for sel in NAME_SELECTORS:
                        try:
                            txt = page.locator(sel).first.inner_text(timeout=2000).strip()
                            if txt:
                                return txt
                        except Exception:
                            continue
                    return ""
                finally:
                    ctx.close()
        except Exception:
            return ""

    # ---- upload ----
    def upload(
        self,
        profile_path: str,
        video_path: str,
        title: str,
        scheduled_time: datetime | None,
        headless: bool = True,
    ) -> tuple[bool, str]:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(profile_path).as_posix()
        video_abs = Path(video_path).resolve().as_posix()

        try:
            with sync_playwright() as p:
                # First attempts run headless (silent background work). PublishQueue
                # flips this to False on retry so the user can solve any captcha
                # that the headless attempt couldn't.
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=headless,
                    viewport={"width": 1280, "height": 900},
                )
                try:
                    page = ctx.new_page() if not ctx.pages else ctx.pages[0]
                    page.set_default_timeout(STEP_TIMEOUT_MS)
                    return self._do_upload(page, video_abs, title, scheduled_time)
                finally:
                    time.sleep(1)
                    ctx.close()
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")

    def _do_upload(self, page, video_abs: str, title: str,
                   scheduled_time: datetime | None) -> tuple[bool, str]:
        # Step A: navigate
        try:
            page.goto(URL_UPLOAD, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        except Exception as e:
            shot = _shoot(page, "nav")
            return (False, f"navigate failed: {e}; screenshot={shot}")

        # Step B: set video file
        try:
            file_input = page.locator(SEL_VIDEO_FILE_INPUT).first
            file_input.set_input_files(video_abs)
        except Exception as e:
            shot = _shoot(page, "set-video")
            return (False, f"set video file failed: {e}; screenshot={shot}")

        # Step C: wait for upload to finish — title input being visible is our signal
        try:
            _try_locators(page, SEL_FORM_READY_CANDIDATES, timeout_ms=FORM_READY_TIMEOUT_MS)
        except Exception as e:
            shot = _shoot(page, "wait-form-ready")
            return (False, f"upload didn't finish or form didn't appear: {e}; screenshot={shot}")

        # Step D: set title
        try:
            title_loc, _sel = _try_locators(page, SEL_TITLE_CANDIDATES)
            try:
                title_loc.fill(title)
            except Exception:
                # contenteditable may not support .fill — use type() instead
                title_loc.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Delete")
                title_loc.type(title)
        except Exception as e:
            shot = _shoot(page, "set-title")
            return (False, f"set title failed: {e}; screenshot={shot}")

        # Step E: cover — skipped on purpose. Douyin uses the video's first
        # frame automatically, and explicitly setting it triggers a cover
        # picker modal that we'd then have to dismiss.

        # Step F: self declaration — optional, appears only for some videos.
        try:
            _handle_self_declaration(page)
        except Exception as e:
            shot = _shoot(page, "self-declaration")
            return (False, f"set self declaration failed: {e}; screenshot={shot}")

        # Step G: scheduled time (optional)
        if scheduled_time is not None:
            try:
                radio, _sel = _try_locators(page, SEL_RADIO_SCHEDULED_CANDIDATES)
                radio.click()
                dt_input, _sel = _try_locators(page, SEL_DATETIME_INPUT_CANDIDATES)
                dt_input.fill(scheduled_time.strftime("%Y-%m-%d %H:%M"))
                page.keyboard.press("Enter")  # close datepicker
            except Exception as e:
                shot = _shoot(page, "set-scheduled")
                return (False, f"set scheduled time failed: {e}; screenshot={shot}")

        # Step H: click publish. Douyin returns to the content list and keeps
        # uploading in a side task window; wait for that in Step I.
        try:
            btn, _sel = _try_locators(page, SEL_PUBLISH_BUTTON_CANDIDATES)
            _click_enabled(btn)
        except Exception as e:
            shot = _shoot(page, "click-publish")
            return (False, f"click publish failed: {e}; screenshot={shot}")

        # Step I: wait for success
        ok, reason = _wait_for_submit_result(page)
        if not ok:
            shot = _shoot(page, "submit-blocked")
            return (False, f"{reason}; screenshot={shot}")

        return (True, "")
