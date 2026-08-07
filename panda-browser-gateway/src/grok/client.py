"""
Grok client — core interaction logic for grok.com.

Sends messages, waits for responses, manages conversations.
Same interface as ChatGPTClient for API-layer compatibility.
"""

from __future__ import annotations

import asyncio
import re
import time

from patchright.async_api import Page

from src.config import Config
from src.grok.selectors import GrokSelectors
from src.grok.detector import (
    wait_for_response_complete,
    extract_last_response_via_copy,
    count_assistant_messages,
    get_latest_assistant_turn_signature,
    is_incomplete_response_text,
)
from src.browser.human import human_type, human_click, thinking_pause, random_delay
from src.chatgpt.models import ChatResponse
from src.log import setup_logging

log = setup_logging("grok_client")


class GrokClient:
    """
    High-level client for Grok (grok.com).

    Requires a Playwright Page logged in to grok.com.
    Same interface as ChatGPTClient for provider-agnostic API usage.
    """

    def __init__(self, page: Page) -> None:
        self._page = page
        self._current_model: str = ""

    @property
    def page(self) -> Page:
        return self._page

    # ── Model selection ──────────────────────────────────────────

    _MODEL_DISPLAY = {
        "grok-3": "Grok 3",
        "grok-3-mini": "Grok 3 mini",
        "grok-2": "Grok 2",
        "grok-2-mini": "Grok 2 mini",
    }
    _MODEL_ALIASES: dict[str, str] = {}

    async def select_model(self, model_id: str) -> bool:
        """Select a model in the Grok UI."""
        resolved = self._MODEL_ALIASES.get(model_id, model_id)
        display = self._MODEL_DISPLAY.get(resolved, "")

        if not display:
            log.debug(f"select_model: unknown Grok model '{model_id}'")
            return False

        if self._current_model == resolved:
            return True

        log.info(f"select_model: switching to '{resolved}' (display='{display}')")

        for sel in GrokSelectors.MODEL_SELECTOR:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(0.5)

                    option = await self._page.query_selector(
                        f"[role='option']:has-text('{display}')"
                    )
                    if option:
                        await option.click()
                        self._current_model = resolved
                        log.info(f"select_model: ✓ switched to '{resolved}'")
                        return True

                    await self._page.keyboard.press("Escape")
                    break
            except Exception:
                continue

        log.warning(f"select_model: could not switch to '{resolved}'")
        return False

    # ── Core: Send & Receive ────────────────────────────────────

    async def send_message(
        self,
        text: str,
        image_paths: list[str] | None = None,
        file_paths: list[str] | None = None,
    ) -> ChatResponse:
        """
        Send a message to Grok and wait for the complete response.

        Returns ChatResponse with the model's reply and metadata.
        """
        start_time = time.time()

        await thinking_pause()

        # Upload files if provided
        all_paths = (image_paths or []) + (file_paths or [])
        if all_paths:
            await self._upload_files(all_paths)

        # Find chat input
        input_selector = await self._find_selector(GrokSelectors.CHAT_INPUT, "chat input")
        if not input_selector:
            raise RuntimeError("Could not find Grok chat input")

        # Count existing turns before sending
        pre_count = await count_assistant_messages(self._page)
        prev_signature = await get_latest_assistant_turn_signature(self._page)

        # Type the message
        try:
            el = await self._page.query_selector(input_selector)
            if el and "textarea" in input_selector:
                await el.click()
                await asyncio.sleep(0.3)
                await self._page.keyboard.insert_text(text)
            else:
                await human_type(self._page, input_selector, text)
        except Exception:
            await human_type(self._page, input_selector, text)

        await random_delay(300, 600)

        # Click send
        sent = await self._click_send()
        if not sent:
            await self._page.keyboard.press("Enter")
            log.debug("Grok: send via Enter key fallback")

        # Wait for response
        await wait_for_response_complete(
            self._page,
            expected_msg_count=pre_count + 1,
            timeout_ms=Config.RESPONSE_TIMEOUT,
            previous_turn_signature=prev_signature,
        )

        await asyncio.sleep(1.0)

        # Extract response
        response_text = await extract_last_response_via_copy(self._page, prev_signature)

        if not response_text:
            response_text = "[Grok response could not be extracted]"

        elapsed_ms = int((time.time() - start_time) * 1000)
        thread_id = self._extract_thread_id()

        log.info(f"Grok response: {len(response_text)} chars in {elapsed_ms}ms")

        return ChatResponse(
            message=response_text,
            thread_id=thread_id,
            response_time_ms=elapsed_ms,
            images=[],
            has_images=False,
        )

    async def new_chat(self) -> None:
        """Start a new Grok conversation."""
        log.info("Grok: starting new chat...")

        for sel in GrokSelectors.NEW_CHAT_BUTTON:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(1.5)
                    log.info("Grok: new chat via button")
                    return
            except Exception:
                continue

        try:
            await self._page.goto(Config.GROK_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            log.info("Grok: new chat via navigation")
        except Exception as e:
            log.warning(f"Grok: new_chat failed: {e}")

    async def navigate_to_thread(self, thread_id: str) -> None:
        url = f"{Config.GROK_URL.rstrip('/')}/chat/{thread_id}"
        await self._page.goto(url, wait_until="domcontentloaded")
        await random_delay(800, 1500)

    async def get_current_thread_url(self) -> str:
        return self._page.url

    async def list_threads(self) -> list[dict]:
        threads = []
        for sel in GrokSelectors.SIDEBAR_THREAD_LINKS:
            try:
                elements = await self._page.query_selector_all(sel)
                for el in elements:
                    href = await el.get_attribute("href") or ""
                    title = (await el.inner_text()).strip()
                    match = re.search(r"/chat/([a-zA-Z0-9_-]+)", href)
                    if match:
                        threads.append({
                            "id": match.group(1),
                            "title": title,
                            "url": f"{Config.GROK_URL.rstrip('/')}{href}",
                        })
                if threads:
                    break
            except Exception:
                continue
        return threads

    # ── Private helpers ──────────────────────────────────────────

    def _extract_thread_id(self) -> str:
        url = self._page.url
        match = re.search(r"/chat/([a-zA-Z0-9_-]+)", url)
        return match.group(1) if match else ""

    async def _find_selector(self, selectors: list[str], name: str) -> str | None:
        for selector in selectors:
            try:
                el = await self._page.wait_for_selector(
                    selector, timeout=Config.SELECTOR_TIMEOUT, state="visible"
                )
                if el:
                    return selector
            except Exception:
                continue
        log.warning(f"No working selector for: {name}")
        return None

    async def _click_send(self) -> bool:
        for sel in GrokSelectors.SEND_BUTTON:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    disabled = await el.get_attribute("disabled")
                    if disabled is not None:
                        continue
                    await human_click(self._page, sel)
                    return True
            except Exception:
                continue
        return False

    async def _upload_files(self, file_paths: list[str]) -> None:
        valid = [p for p in file_paths if p]
        if not valid:
            return

        for sel in GrokSelectors.FILE_UPLOAD_INPUT:
            try:
                el = await self._page.query_selector(sel)
                if el:
                    await el.set_input_files(valid)
                    await asyncio.sleep(3 + len(valid))
                    return
            except Exception:
                continue

        log.warning("Grok: could not find file upload input")
