"""Xiaohongshu (creator.xiaohongshu.com) Publisher.

Login + name detection are implemented. Upload is not yet supported —
implement when the user prioritizes XHS publishing.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from publisher.base import Publisher


URL_HOME = "https://creator.xiaohongshu.com/new/home"
URL_LOGIN = "https://creator.xiaohongshu.com/new/home"

NAME_SELECTORS = [
    "div.user-name",
    "span.user-name",
    "[class*='nickname']",
]

NAV_TIMEOUT = 15_000
LOGIN_DETECT_WAIT = 2_500


class XiaohongshuPublisher(Publisher):
    platform = "xiaohongshu"
    display_name = "小红书"
    login_url = URL_LOGIN
    creator_home_url = URL_HOME
    # XHS often redirects to a /login/ subpath when not authenticated
    login_url_markers = ("/login", "/sign", "?xhsshare")

    def check_login(self, profile_path: str) -> bool:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(profile_path).as_posix()
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(user_data_dir, headless=True)
                try:
                    page = ctx.new_page() if not ctx.pages else ctx.pages[0]
                    page.goto(URL_HOME, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                    page.wait_for_timeout(LOGIN_DETECT_WAIT)
                    return not any(m in page.url for m in self.login_url_markers)
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
                    page.goto(URL_HOME, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                    page.wait_for_timeout(LOGIN_DETECT_WAIT)
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

    def upload(self, profile_path, video_path, title, scheduled_time, headless=True):
        return (False, "小红书上传暂未实现")
