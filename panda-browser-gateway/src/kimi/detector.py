"""
Response completion detector for Kimi (kimi.moonshot.cn).

Follows the same interface as the ChatGPT/Claude detectors.
"""

from __future__ import annotations

import asyncio

from patchright.async_api import Page

from src.kimi.selectors import KimiSelectors
from src.log import setup_logging
from src.config import Config

log = setup_logging("kimi_detector")


async def count_assistant_messages(page: Page) -> int:
    """Count assistant turns on the page."""
    count = await page.evaluate(
        """
        () => {
            const sels = [
                'div[data-role="assistant"]',
                '.kimi-message.assistant',
                '.message-content',
            ];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                if (els.length > 0) return els.length;
            }
            return 0;
        }
        """
    )
    return int(count or 0)


async def get_latest_assistant_turn_signature(page: Page) -> str | None:
    """Return a stable signature for the latest assistant turn."""
    text = await page.evaluate(
        """
        () => {
            const sels = [
                'div[data-role="assistant"]',
                '.kimi-message.assistant',
                '.markdown-body',
            ];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                if (els.length > 0) {
                    return els[els.length - 1].innerText.trim().slice(0, 80);
                }
            }
            return null;
        }
        """
    )
    return text if text else None


def is_incomplete_response_text(text: str | None) -> bool:
    if not text:
        return True
    lower = text.lower()
    return any(m in lower for m in ["thinking", "generating", "loading", "▋"])


async def wait_for_response_complete(
    page: Page,
    expected_msg_count: int | None = None,
    timeout_ms: int | None = None,
    previous_turn_signature: str | None = None,
) -> bool:
    """Wait until Kimi finishes generating its response."""
    timeout = timeout_ms or Config.RESPONSE_TIMEOUT
    log.info(f"Waiting for Kimi response (timeout={timeout}ms)...")

    poll_interval = Config.POLL_INTERVAL_MS / 1000
    elapsed = 0.0
    stop_sels = KimiSelectors.STOP_BUTTON

    stop_visible = False
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
        while elapsed * 1000 < timeout:
            visible = False
            for sel in stop_sels:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    visible = True
                    break
            if not visible:
                log.info("Kimi response complete")
                await asyncio.sleep(0.5)
                return True
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    log.info("Kimi: falling back to text-stability detection...")
    last_text = ""
    stable_count = 0

    while elapsed * 1000 < timeout:
        text = await extract_last_response_via_copy(page)
        if text and text == last_text and not is_incomplete_response_text(text):
            stable_count += 1
            if stable_count >= 3:
                log.info("Kimi response text stabilized")
                return True
        else:
            stable_count = 0
            last_text = text
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    log.warning(f"Kimi response timeout after {int(elapsed)}s")
    return False


async def extract_last_response_via_copy(
    page: Page,
    previous_turn_signature: str | None = None,
) -> str:
    """Extract the latest assistant message from Kimi."""
    try:
        await page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        await page.evaluate("navigator.clipboard.writeText('').catch(() => {})")

        copy_clicked = await page.evaluate(
            """
            () => {
                const sels = [
                    'button[aria-label="Copy"]',
                    'button[title="Copy"]',
                    'button[data-testid="copy-button"]',
                ];
                for (const s of sels) {
                    const btns = document.querySelectorAll(s);
                    if (btns.length > 0) {
                        const last = btns[btns.length - 1];
                        if (last.offsetParent !== null) { last.click(); return true; }
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
        log.debug(f"Kimi copy button failed: {e}")

    text = await page.evaluate(
        """
        () => {
            const sels = [
                'div[data-role="assistant"]',
                '.kimi-message.assistant',
                '.markdown-body',
            ];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                if (els.length > 0) return els[els.length - 1].innerText.trim();
            }
            return '';
        }
        """
    )
    return (text or "").strip()
