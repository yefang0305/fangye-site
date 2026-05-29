"""Abstract Publisher interface.

Each platform (Douyin, Xiaohongshu, Kuaishou, ...) implements this.
The publish queue dispatches tasks to the right Publisher based on
the account's `platform` field. The account panel uses login_url /
creator_home_url / detect_account_name for the QR-add flow and the
"open creator backend" double-click action.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class Publisher(ABC):
    # ---- platform metadata (override in subclasses) ----
    platform: str = ""           # short id, e.g. "douyin"
    display_name: str = ""       # for UI, e.g. "抖音"
    login_url: str = ""          # where the user lands to scan QR
    creator_home_url: str = ""   # where the creator backend lives

    # URL substrings that indicate "not logged in"
    login_url_markers: tuple[str, ...] = ("/login", "/passport")

    # ---- behaviors ----
    @abstractmethod
    def check_login(self, profile_path: str) -> bool:
        """Return True if the profile is logged in, False otherwise."""

    @abstractmethod
    def detect_account_name(self, profile_path: str) -> str:
        """After login, read the account display name from the creator
        backend page. Returns empty string if not detectable."""

    @abstractmethod
    def upload(
        self,
        profile_path: str,
        video_path: str,
        title: str,
        scheduled_time: datetime | None,
        headless: bool = True,
    ) -> tuple[bool, str]:
        """Upload a video. scheduled_time=None means publish immediately;
        otherwise submit it to the platform's scheduler at that time.

        headless: True for normal silent uploads. Set to False on retries
        when account weight may trigger a captcha — the visible browser
        window lets the user solve it manually.

        Returns (success, error_msg). error_msg is '' on success.
        """
