"""Open the platform's creator backend in a browser bound to a specific
account profile.

Today we spawn an independent (non-headless) Chromium window via Playwright.
The abstraction `BrowserLauncher.open_creator_backend(...)` lets us swap in
a Qt-embedded WebEngine implementation later without touching callers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import threading


class BrowserLauncher(ABC):
    @abstractmethod
    def open_creator_backend(self, profile_path: str, url: str) -> None:
        """Open `url` in a browser bound to the given Chromium profile.

        Must return quickly (non-blocking from the UI's perspective);
        the browser keeps running until the user closes it.
        """


class IndependentChromiumLauncher(BrowserLauncher):
    """Spawn a separate Chromium window via Playwright. The browser keeps
    running on its own thread until the user closes it manually."""

    def open_creator_backend(self, profile_path: str, url: str) -> None:
        target = threading.Thread(
            target=self._run, args=(profile_path, url), daemon=True
        )
        target.start()

    @staticmethod
    def _run(profile_path: str, url: str) -> None:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(profile_path).as_posix()
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,
                    viewport={"width": 1280, "height": 800},
                )
                page = ctx.new_page() if not ctx.pages else ctx.pages[0]
                page.goto(url)
                # Block until user closes the browser
                ctx.wait_for_event("close", timeout=0)
        except Exception:
            # If the user closes via the X button before we attach the close
            # listener, Playwright raises — that's expected, ignore.
            pass
