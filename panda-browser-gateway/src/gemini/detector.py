"""
Response completion detector for Google AI Studio.

Primary strategy: wait for the stop button to disappear, then
check that a copy button is present (or text has stabilized).
"""

from __future__ import annotations

import asyncio

from patchright.async_api import Page

from src.gemini.selectors import GeminiSelectors
from src.log import setup_logging
from src.config import Config

log = setup_logging("gemini_detector")


async def count_assistant_messages(page: Page) -> int:
    """Count model response turns on the page."""
    count = await page.evaluate(
        """
        () => {
            const sel = [
                'ms-chat-turn[role="model"]',
                '.model-response-text',
                'ms-model-response',
                '[data-role="model"]',
            ];
            for (const s of sel) {
                const els = document.querySelectorAll(s);
                if (els.length > 0) return els.length;
            }
            return 0;
        }
        """
    )
    return int(count or 0)


async def get_latest_assistant_turn_signature(page: Page) -> str | None:
    """Return a stable signature for the latest model turn."""
    text = await page.evaluate(
        """
        () => {
            const sels = [
                'ms-chat-turn[role="model"]',
                '.model-response-text',
                'ms-model-response',
            ];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                if (els.length > 0) {
                    const last = els[els.length - 1];
                    return last.innerText.trim().slice(0, 80);
                }
            }
            return null;
        }
        """
    )
    return text if text else None


def is_incomplete_response_text(text: str | None) -> bool:
    """True when text looks like a transient status."""
    if not text:
        return True
    lower = text.lower()
    return any(m in lower for m in ["thinking", "generating", "loading"])


async def wait_for_response_complete(
    page: Page,
    expected_msg_count: int | None = None,
    timeout_ms: int | None = None,
    previous_turn_signature: str | None = None,
) -> bool:
    """Wait until Gemini finishes generating its response."""
    timeout = timeout_ms or Config.RESPONSE_TIMEOUT
    log.info(f"Waiting for Gemini response (timeout={timeout}ms)...")

    poll_interval = Config.POLL_INTERVAL_MS / 1000
    elapsed = 0.0

    # Phase 1: wait for stop button to disappear (streaming in progress)
    stop_sels = GeminiSelectors.STOP_BUTTON
    stop_visible = False

    # Check if stop button appeared within 10s
    while elapsed * 1000 < min(10000, timeout):
        for sel in stop_sels:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                stop_visible = True
                break
        if stop_visible:
            break
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    if stop_visible:
        log.debug("Stop button visible — waiting for it to disappear...")
        while elapsed * 1000 < timeout:
            visible = False
            for sel in stop_sels:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    visible = True
                    break
            if not visible:
                log.info("Gemini response complete — stop button gone")
                await asyncio.sleep(0.5)
                return True
            if elapsed > 0 and int(elapsed) % 10 == 0:
                log.debug(f"Still generating... ({int(elapsed)}s)")
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    # Phase 2: text stability fallback
    log.info("Falling back to text-stability detection for Gemini...")
    last_text = ""
    stable_count = 0
    required_stable = 3

    while elapsed * 1000 < timeout:
        text = await extract_last_response_via_copy(page)
        if text and text == last_text:
            stable_count += 1
            if stable_count >= required_stable:
                if not is_incomplete_response_text(text):
                    log.info("Gemini response text stabilized")
                    return True
                stable_count = 0
        else:
            stable_count = 0
            last_text = text
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    log.warning(f"Gemini response timeout after {int(elapsed)}s")
    return False


async def extract_last_response_via_copy(
    page: Page,
    previous_turn_signature: str | None = None,
) -> str:
    """Extract the latest model response from AI Studio."""
    # Try clipboard via copy button first
    try:
        await page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        await page.evaluate("navigator.clipboard.writeText('').catch(() => {})")

        copy_clicked = await page.evaluate(
            """
            () => {
                const sels = [
                    'button[aria-label="Copy response"]',
                    'button[aria-label="Copy"]',
                    'ms-copy-button button',
                    'button[mattooltip="Copy"]',
                ];
                for (const s of sels) {
                    const btns = document.querySelectorAll(s);
                    if (btns.length > 0) {
                        const last = btns[btns.length - 1];
                        if (last.offsetParent !== null) {
                            last.click();
                            return true;
                        }
                    }
                }
                return false;
            }
            """
        )
        if copy_clicked:
            await asyncio.sleep(0.8)
            text = await page.evaluate("navigator.clipboard.readText().catch(() => '')")
            if text and text.strip():
                return text.strip()
    except Exception as e:
        log.debug(f"Copy button extraction failed: {e}")

    # Fallback: DOM extraction
    text = await page.evaluate(
        """
        () => {
            const sels = [
                'ms-chat-turn[role="model"] .model-response-text',
                '.model-response-text',
                'ms-model-response',
                '[data-role="model"]',
            ];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                if (els.length > 0) {
                    return els[els.length - 1].innerText.trim();
                }
            }
            return '';
        }
        """
    )
    return (text or "").strip()
