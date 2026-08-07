"""
Gemini AI Studio client — core interaction logic.

Sends messages to aistudio.google.com, waits for responses.
Same interface as ChatGPTClient / ClaudeClient for API-layer compatibility.
"""

from __future__ import annotations

import asyncio
import re
import time

from patchright.async_api import Page

from src.config import Config
from src.gemini.selectors import GeminiSelectors
from src.gemini.detector import (
    wait_for_response_complete,
    extract_last_response_via_copy,
    count_assistant_messages,
    get_latest_assistant_turn_signature,
    is_incomplete_response_text,
)
from src.browser.human import human_type, human_click, thinking_pause, random_delay
from src.chatgpt.models import ChatResponse
from src.log import setup_logging

log = setup_logging("gemini_client")


class GeminiClient:
    """
    High-level client for Google AI Studio.

    Requires a Playwright Page logged in to aistudio.google.com.
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
        "gemini-2.0-flash": "Gemini 2.0 Flash",
        "gemini-1.5-pro": "Gemini 1.5 Pro",
        "gemini-2.0-flash-thinking": "Gemini 2.0 Flash Thinking",
        "gemini-1.5-flash": "Gemini 1.5 Flash",
        "gemini-1.0-pro": "Gemini 1.0 Pro",
    }
    _MODEL_ALIASES: dict[str, str] = {}

    async def select_model(self, model_id: str) -> bool:
        """Select a model in the AI Studio UI."""
        resolved = self._MODEL_ALIASES.get(model_id, model_id)
        display = self._MODEL_DISPLAY.get(resolved, "")

        if not display:
            log.debug(f"select_model: unknown Gemini model '{model_id}'")
            return False

        if self._current_model == resolved:
            return True

        log.info(f"select_model: switching to '{resolved}' (display='{display}')")

        for sel in GeminiSelectors.MODEL_SELECTOR:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(0.5)

                    # Find and click the model option
                    option = await self._page.query_selector(
                        f"mat-option:has-text('{display}')"
                    )
                    if option and await option.is_visible():
                        await option.click()
                        await asyncio.sleep(0.5)
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
        Send a message to Gemini AI Studio and wait for the complete response.

        Returns ChatResponse with the model's reply and metadata.
        """
        start_time = time.time()

        await thinking_pause()

        # Upload files if provided
        all_paths = (image_paths or []) + (file_paths or [])
        if all_paths:
            await self._upload_files(all_paths)

        # Find chat input
        input_selector = await self._find_selector(GeminiSelectors.CHAT_INPUT, "chat input")
        if not input_selector:
            raise RuntimeError("Could not find Gemini chat input")

        # Count existing turns before sending
        pre_count = await count_assistant_messages(self._page)
        prev_signature = await get_latest_assistant_turn_signature(self._page)

        # Type the message
        await human_type(self._page, input_selector, text)
        await random_delay(300, 600)

        # Click send
        sent = await self._click_send()
        if not sent:
            # Fallback: Enter key
            await self._page.keyboard.press("Enter")
            log.debug("Send via Enter key fallback")

        # Wait for response
        await wait_for_response_complete(
            self._page,
            expected_msg_count=pre_count + 1,
            timeout_ms=Config.RESPONSE_TIMEOUT,
            previous_turn_signature=prev_signature,
        )

        # Brief settle
        await asyncio.sleep(1.0)

        # Extract response
        response_text = await extract_last_response_via_copy(self._page, prev_signature)

        if not response_text:
            response_text = "[Gemini response could not be extracted]"

        elapsed_ms = int((time.time() - start_time) * 1000)
        thread_id = self._extract_thread_id()

        log.info(f"Gemini response: {len(response_text)} chars in {elapsed_ms}ms")

        return ChatResponse(
            message=response_text,
            thread_id=thread_id,
            response_time_ms=elapsed_ms,
            images=[],
            has_images=False,
        )

    async def new_chat(self) -> None:
        """Start a new conversation in AI Studio."""
        log.info("Gemini: starting new chat...")
        target_url = Config.GEMINI_URL

        # Try new chat button first
        for sel in GeminiSelectors.NEW_CHAT_BUTTON:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(1.5)
                    log.info("Gemini: new chat via button")
                    return
            except Exception:
                continue

        # Navigate to new prompt URL
        try:
            await self._page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            log.info("Gemini: new chat via navigation")
        except Exception as e:
            log.warning(f"Gemini: new_chat navigation failed: {e}")

    async def navigate_to_thread(self, thread_id: str) -> None:
        """Navigate to a specific conversation."""
        log.info(f"Gemini: navigate to thread {thread_id}")
        # AI Studio doesn't have a simple thread URL scheme; navigate to base URL
        await self._page.goto(Config.GEMINI_URL, wait_until="domcontentloaded")
        await random_delay(800, 1500)

    async def get_current_thread_url(self) -> str:
        return self._page.url

    async def list_threads(self) -> list[dict]:
        """AI Studio doesn't have a sidebar thread list — return empty."""
        return []

    # ── Private helpers ──────────────────────────────────────────

    def _extract_thread_id(self) -> str:
        """Extract thread ID from the current URL."""
        url = self._page.url
        match = re.search(r"/prompts/([a-zA-Z0-9_-]+)", url)
        return match.group(1) if match else ""

    async def _find_selector(self, selectors: list[str], name: str) -> str | None:
        """Try each selector in fallback order. Return the first match."""
        for selector in selectors:
            try:
                el = await self._page.wait_for_selector(
                    selector,
                    timeout=Config.SELECTOR_TIMEOUT,
                    state="visible",
                )
                if el:
                    log.debug(f"Found {name} via: {selector}")
                    return selector
            except Exception:
                continue
        log.warning(f"No working selector for: {name}")
        return None

    async def _click_send(self) -> bool:
        """Click the send / run button."""
        for sel in GeminiSelectors.SEND_BUTTON:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    is_disabled = await el.get_attribute("disabled")
                    if is_disabled is not None:
                        continue
                    await human_click(self._page, sel)
                    log.debug(f"Send clicked: {sel}")
                    return True
            except Exception:
                continue
        return False

    async def _upload_files(self, file_paths: list[str]) -> None:
        """Upload files to AI Studio."""
        valid = [p for p in file_paths if p]
        if not valid:
            return

        for sel in GeminiSelectors.FILE_UPLOAD_INPUT:
            try:
                el = await self._page.query_selector(sel)
                if el:
                    await el.set_input_files(valid)
                    wait_time = 3 + len(valid)
                    log.info(f"Gemini: uploaded {len(valid)} file(s), waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    return
            except Exception as e:
                log.debug(f"Gemini file upload failed with {sel}: {e}")
                continue

        log.warning("Gemini: could not find file upload input")
