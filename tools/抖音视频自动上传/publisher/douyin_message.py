"""Douyin stranger-message scraping and manual reply support.

Selectors are documented in docs/selectors_message.md. When Douyin changes
the creator-message page, update these constants first.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from publisher.message_reader import ChatMessage, Message, MessageReader


URL_CHAT = "https://creator.douyin.com/creator-micro/data/following/chat"

SEL_CONV_ITEMS = "li.semi-list-item"
SEL_CONV_USERNAME = '[class^="item-header-name-"]'
SEL_CONV_AVATAR = "img"
SEL_CONV_PREVIEW = '[class^="item-content-"] [class^="text-"]'
SEL_CONV_TIME = '[class^="item-header-time-"]'
SEL_CONV_UNREAD = ".semi-badge-primary"

SEL_REPLY_INPUT = '.chat-input-nSWBco[contenteditable="true"]'
SEL_REPLY_SEND = 'button.chat-btn:has-text("发送")'
SEL_REPLY_HISTORY_MESSAGES = '[class^="box-item-message-"] pre'
SEL_DETAIL_READY = SEL_REPLY_INPUT

NAV_TIMEOUT_MS = 20_000
TAB_SWITCH_WAIT_MS = 1_500
AFTER_SEND_SETTLE_MS = 5_000


def normalize_avatar_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url


def conversation_id_from_parts(user_name: str, avatar_url: str) -> str:
    """Build a stable-enough id from fields Douyin exposes in the DOM."""
    avatar_path = avatar_url.split("?", 1)[0].rstrip("/")
    avatar_id = avatar_path.rsplit("/", 1)[-1] if avatar_path else ""
    raw = f"{user_name}_{avatar_id}" if avatar_id else user_name
    return re.sub(r"\s+", " ", raw).strip()


def _safe_inner_text(locator, timeout: int = 1000) -> str:
    try:
        return locator.inner_text(timeout=timeout).strip()
    except Exception:
        return ""


def _safe_attr(locator, attr: str, timeout: int = 1000) -> str:
    try:
        return locator.get_attribute(attr, timeout=timeout) or ""
    except Exception:
        return ""


class DouyinMessageReader(MessageReader):
    platform = "douyin"

    def fetch_unread_strangers(
        self,
        account_id: int,
        account_name: str,
        profile_path: str,
    ) -> list[Message]:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(profile_path).as_posix()
        results: dict[str, Message] = {}
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 800},
                )
                try:
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                    page.goto(URL_CHAT, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                    for tab_name in ("全部", "陌生人私信"):
                        self._open_message_tab(page, tab_name)
                        for message in self._scrape_unread_visible_items(page, account_id, account_name):
                            results[message.conversation_id] = message
                finally:
                    ctx.close()
        except Exception:
            return []
        return list(results.values())

    def reply(self, profile_path: str, conversation_id: str, text: str) -> tuple[bool, str]:
        from playwright.sync_api import sync_playwright

        if not text.strip():
            return (False, "empty reply text")

        user_data_dir = Path(profile_path).as_posix()
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 800},
                )
                try:
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                    page.goto(URL_CHAT, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                    target = self._find_conversation_item_in_tabs(page, conversation_id)
                    if target is None:
                        return (False, f"conversation not found: {conversation_id}")

                    target.click(timeout=NAV_TIMEOUT_MS)
                    page.locator(SEL_REPLY_INPUT).first.wait_for(
                        state="visible",
                        timeout=NAV_TIMEOUT_MS,
                    )
                    input_box = page.locator(SEL_REPLY_INPUT).first
                    input_box.click()
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Delete")
                    page.keyboard.insert_text(text)

                    send_button = page.locator(SEL_REPLY_SEND).first
                    page.wait_for_function(
                        """() => {
                            const btn = Array.from(document.querySelectorAll('button.chat-btn'))
                                .find(b => (b.innerText || '').trim() === '发送');
                            return !!btn && !btn.disabled && !btn.className.includes('semi-button-disabled');
                        }""",
                        timeout=NAV_TIMEOUT_MS,
                    )
                    send_button.click(timeout=NAV_TIMEOUT_MS)
                    page.wait_for_function(
                        """(text) => {
                            const input = document.querySelector('.chat-input-nSWBco[contenteditable="true"]');
                            const empty = !input || !(input.innerText || '').trim();
                            const messages = Array.from(document.querySelectorAll('[class^="box-item-message-"] pre'))
                                .map(el => (el.innerText || '').trim());
                            return empty && messages.includes(text);
                        }""",
                        arg=text,
                        timeout=NAV_TIMEOUT_MS,
                    )
                    page.wait_for_timeout(AFTER_SEND_SETTLE_MS)
                    return (True, "")
                finally:
                    ctx.close()
        except Exception as exc:
            return (False, f"{type(exc).__name__}: {exc}")

    def fetch_conversation_messages(self, profile_path: str, conversation_id: str) -> list[ChatMessage]:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(profile_path).as_posix()
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=True,
                    viewport={"width": 1280, "height": 800},
                )
                try:
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                    page.goto(URL_CHAT, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                    target = self._find_conversation_item_in_tabs(page, conversation_id)
                    if target is None:
                        return []
                    target.click(timeout=NAV_TIMEOUT_MS)
                    page.locator(SEL_DETAIL_READY).first.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
                    page.wait_for_timeout(TAB_SWITCH_WAIT_MS)
                    return self._scrape_visible_chat_messages(page)
                finally:
                    ctx.close()
        except Exception:
            return []

    def _open_message_tab(self, page, tab_name: str) -> None:
        page.get_by_role("tab", name=tab_name).click(timeout=NAV_TIMEOUT_MS)
        page.wait_for_function(
            """() => {
                if (document.querySelectorAll('li.semi-list-item').length > 0) return true;
                return document.body.innerText.includes('没有更多');
            }""",
            timeout=NAV_TIMEOUT_MS,
        )
        page.wait_for_timeout(TAB_SWITCH_WAIT_MS)

    def _scrape_unread_visible_items(self, page, account_id: int, account_name: str) -> list[Message]:
        messages: list[Message] = []
        for item in page.locator(SEL_CONV_ITEMS).all():
            try:
                if item.locator(SEL_CONV_UNREAD).count() <= 0:
                    continue
                user_name = _safe_inner_text(item.locator(SEL_CONV_USERNAME).first)
                avatar = normalize_avatar_url(_safe_attr(item.locator(SEL_CONV_AVATAR).first, "src"))
                preview = _safe_inner_text(item.locator(SEL_CONV_PREVIEW).first)
                timestamp = _safe_inner_text(item.locator(SEL_CONV_TIME).first)
                conversation_id = conversation_id_from_parts(user_name, avatar)
                if not user_name or not conversation_id:
                    continue
                messages.append(
                    Message(
                        account_id=account_id,
                        account_name=account_name,
                        conversation_id=conversation_id,
                        user_name=user_name,
                        user_avatar_url=avatar,
                        preview=preview,
                        timestamp_str=timestamp,
                        fetched_at=datetime.now(),
                    )
                )
            except Exception:
                continue
        return messages

    def _find_conversation_item_in_tabs(self, page, conversation_id: str):
        for tab_name in ("全部", "陌生人私信"):
            self._open_message_tab(page, tab_name)
            target = self._find_conversation_item(page, conversation_id)
            if target is not None:
                return target
        return None

    def _find_conversation_item(self, page, conversation_id: str):
        for item in page.locator(SEL_CONV_ITEMS).all():
            user_name = _safe_inner_text(item.locator(SEL_CONV_USERNAME).first)
            avatar = normalize_avatar_url(_safe_attr(item.locator(SEL_CONV_AVATAR).first, "src"))
            if conversation_id_from_parts(user_name, avatar) == conversation_id:
                return item
        return None

    def _scrape_visible_chat_messages(self, page) -> list[ChatMessage]:
        rows = page.evaluate(
            """() => {
                const out = [];
                const pres = Array.from(document.querySelectorAll('[class^="box-item-message-"] pre'));
                for (const pre of pres) {
                    let box = pre.parentElement;
                    while (box) {
                        const cls = (box.className || '').toString();
                        if (cls.includes('box-item-') && !cls.includes('box-item-message-')) break;
                        box = box.parentElement;
                    }
                    const cls = box && (box.className || '').toString();
                    out.push({
                        sender: cls && cls.includes('is-me-') ? 'me' : 'peer',
                        text: (pre.innerText || '').trim(),
                        timestamp_str: ''
                    });
                }
                return out;
            }"""
        )
        return [
            ChatMessage(
                sender=str(row.get("sender") or "peer"),
                text=str(row.get("text") or ""),
                timestamp_str=str(row.get("timestamp_str") or ""),
            )
            for row in rows
            if str(row.get("text") or "").strip()
        ]
