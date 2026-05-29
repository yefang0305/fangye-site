"""Account lifecycle: import existing profiles, add new via QR scan,
batch login refresh.

The manager owns the on-disk `profiles_dir` and keeps the SQLite store
in sync with what's there.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from db.store import Store

if TYPE_CHECKING:
    from publisher.base import Publisher


_DEFAULT_PLATFORM = "douyin"


class AccountManager:
    def __init__(self, store: Store, profiles_dir: str, publishers: dict[str, "Publisher"] | None = None):
        self._store = store
        self._profiles_dir = Path(profiles_dir)
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._publishers = publishers or {}

    # ---- add via QR scan (interactive Playwright) ----
    def add_via_qr(
        self,
        group_id: int,
        platform: str = _DEFAULT_PLATFORM,
        timeout_sec: int = 300,
    ) -> tuple[int, str]:
        """Open the platform's login URL in a non-headless browser, wait for
        the user to scan the QR code, then save the profile and try to detect
        the account display name from the creator backend.

        Returns (account_id, detected_display_name). Falls back to a synthetic
        name like "未识别_<platform>_<id>" if detection fails. Caller can
        rename later via the UI.

        Raises ValueError if no Publisher is registered for the platform.
        Raises TimeoutError on QR-scan timeout.
        """
        from playwright.sync_api import sync_playwright

        publisher = self._publishers.get(platform)
        if publisher is None:
            raise ValueError(f"no publisher registered for platform: {platform}")

        # Reserve account id with placeholder name so we have a profile dir
        placeholder_name = f"未识别_{platform}_pending"
        account_id = self._store.add_account(group_id, platform, placeholder_name, "")
        target = self._profiles_dir / str(account_id)
        target.mkdir(parents=True, exist_ok=False)

        try:
            import time as _time
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=str(target),
                    headless=False,
                )
                page = ctx.new_page() if not ctx.pages else ctx.pages[0]
                page.goto(publisher.login_url, wait_until="domcontentloaded", timeout=15000)

                markers = publisher.login_url_markers

                # Step 1: give Douyin/XHS/KS up to 10s to redirect to login page if needed.
                # We can't trust wait_until=networkidle alone since some platforms
                # do a client-side JS redirect after first paint.
                redirect_deadline = _time.time() + 10
                while _time.time() < redirect_deadline:
                    if any(m in page.url for m in markers):
                        break
                    _time.sleep(0.5)

                # Step 2: if URL still has no markers, the user was already logged in.
                if not any(m in page.url for m in markers):
                    pass  # already logged in via prior cookies
                else:
                    # Step 3: wait for user to complete login (URL no longer contains markers).
                    markers_js = ",".join(repr(m) for m in markers)
                    page.wait_for_function(
                        f"""() => {{
                            const ms = [{markers_js}];
                            return !ms.some(m => location.href.includes(m));
                        }}""",
                        timeout=timeout_sec * 1000,
                    )
                    # Tiny grace period for cookies to fully persist.
                    _time.sleep(2)
                ctx.close()
        except Exception:
            self._store.delete_account(account_id)
            shutil.rmtree(target, ignore_errors=True)
            raise

        self._store._conn.execute(
            "UPDATE accounts SET profile_path = ? WHERE id = ?",
            (str(target), account_id),
        )
        self._store._conn.commit()

        # Try to auto-detect display name. Failure is non-fatal.
        detected = ""
        try:
            detected = publisher.detect_account_name(str(target))
        except Exception:
            detected = ""
        final_name = detected.strip() or f"未识别_{platform}_{account_id}"
        self._store.update_account_display_name(account_id, final_name)
        return account_id, final_name

    # ---- delete account + on-disk profile ----
    def delete_account_with_files(self, account_id: int) -> None:
        accounts = [a for a in self._store.list_accounts() if a["id"] == account_id]
        if not accounts:
            return
        profile_path = accounts[0]["profile_path"]
        self._store.delete_account(account_id)
        if profile_path:
            shutil.rmtree(profile_path, ignore_errors=True)

    # ---- batch login refresh ----
    def refresh_all_login_status(self) -> dict[int, bool]:
        """Check login status for every account (active or not). Updates is_active
        accordingly. If login OK and the display_name still looks like a
        placeholder (starts with "未识别_"), try to detect the real name and
        update the record.

        Returns {account_id: is_logged_in}.
        """
        result: dict[int, bool] = {}
        for acc in self._store.list_accounts():
            pub = self._publishers.get(acc["platform"])
            if pub is None or not acc["profile_path"]:
                continue
            try:
                ok = pub.check_login(acc["profile_path"])
            except Exception:
                ok = False
            result[acc["id"]] = ok
            self._store.update_account_active(acc["id"], 1 if ok else 0)
            if ok and acc["display_name"].startswith("未识别_"):
                try:
                    name = pub.detect_account_name(acc["profile_path"]).strip()
                except Exception:
                    name = ""
                if name:
                    self._store.update_account_display_name(acc["id"], name)
        return result
