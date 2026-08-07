"""
BrowserPool — manages N concurrent Chromium instances.

Each slot holds a (BrowserManager, client) pair. Requests acquire a free
slot, run, then release it. If the pool is full the request waits.

Usage:
    pool = BrowserPool(size=3, provider="chatgpt")
    await pool.start()

    async with pool.acquire() as client:
        response = await client.send_message("Hello")

    await pool.close()
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from src.config import Config
from src.log import setup_logging

log = setup_logging("browser_pool")


class _Slot:
    """One (BrowserManager, client) pair."""

    def __init__(self, index: int) -> None:
        self.index = index
        self.browser = None
        self.client = None
        self.healthy = False

    def data_dir(self, provider: str) -> Path:
        suffix = f"_{self.index}" if self.index > 0 else ""
        return Config.PROJECT_ROOT / f"browser_data_{provider}{suffix}"


class BrowserPool:
    """
    Pool of N browser instances for concurrent request handling.

    When POOL_SIZE=1 (default) behaviour is identical to the original
    single-browser + asyncio.Lock approach, but with health-check support.
    """

    def __init__(self, size: int, provider: str) -> None:
        self._size = max(1, size)
        self._provider = provider
        self._slots: list[_Slot] = [_Slot(i) for i in range(self._size)]
        self._queue: asyncio.Queue[_Slot] = asyncio.Queue()
        self._started = False

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(self) -> None:
        """Launch all browsers and push healthy slots into the queue."""
        log.info(f"BrowserPool starting — size={self._size}, provider={self._provider}")
        tasks = [self._init_slot(slot) for slot in self._slots]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._started = True

        healthy = sum(1 for s in self._slots if s.healthy)
        if healthy == 0:
            raise RuntimeError("BrowserPool: no healthy browser could be started")
        log.info(f"BrowserPool ready — {healthy}/{self._size} browsers healthy")

    async def close(self) -> None:
        """Close all browsers gracefully."""
        log.info("BrowserPool closing all browsers...")
        tasks = []
        for slot in self._slots:
            if slot.browser is not None:
                tasks.append(slot.browser.close())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        log.info("BrowserPool closed")

    # ── Acquire / Release ────────────────────────────────────────

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[object, None]:
        """
        Context manager: grab a free browser slot, yield the client.
        Waits indefinitely if all slots are busy (back-pressure).
        Auto-replaces crashed slots.
        """
        slot: _Slot = await self._queue.get()
        log.debug(f"Pool slot {slot.index} acquired")
        try:
            # Health check — restart if crashed
            if not slot.healthy or slot.client is None:
                log.warning(f"Slot {slot.index} unhealthy — attempting restart")
                await self._init_slot(slot)
                if not slot.healthy:
                    raise RuntimeError(f"Pool slot {slot.index} failed to restart")

            yield slot.client
        finally:
            await self._queue.put(slot)
            log.debug(f"Pool slot {slot.index} released")

    @property
    def size(self) -> int:
        return self._size

    @property
    def available(self) -> int:
        return self._queue.qsize()

    # ── Private ──────────────────────────────────────────────────

    async def _init_slot(self, slot: _Slot) -> None:
        """Launch one browser + client. Mark healthy on success."""
        from src.browser.manager import BrowserManager
        from src.browser.auto_login import ensure_logged_in

        slot.healthy = False

        # Close existing browser if restarting
        if slot.browser is not None:
            try:
                await slot.browser.close()
            except Exception:
                pass
            slot.browser = None
            slot.client = None

        data_dir = slot.data_dir(self._provider)
        log.info(f"Slot {slot.index}: launching browser (data_dir={data_dir})")

        try:
            browser = BrowserManager(user_data_dir=data_dir)
            page = await browser.start()
            await browser.apply_stealth_patches()

            # Navigate to provider
            target_url = Config.provider_url()
            await browser.navigate(page, target_url)

            # Auto-login check
            try:
                await ensure_logged_in(page, Config.PROVIDER)
            except Exception as e:
                log.warning(f"Slot {slot.index}: login check failed (may already be logged in): {e}")

            # Build client
            if Config.PROVIDER == "claude":
                from src.claude.client import ClaudeClient
                client = ClaudeClient(page)
            elif Config.PROVIDER == "gemini":
                # Gemini client (Sprint 2)
                try:
                    from src.gemini.client import GeminiClient
                    client = GeminiClient(page)
                except ImportError:
                    from src.chatgpt.client import ChatGPTClient
                    client = ChatGPTClient(page)
                    log.warning("Slot %d: GeminiClient not yet available, using ChatGPTClient stub", slot.index)
            elif Config.PROVIDER == "deepseek":
                try:
                    from src.deepseek.client import DeepSeekClient
                    client = DeepSeekClient(page)
                except ImportError:
                    from src.chatgpt.client import ChatGPTClient
                    client = ChatGPTClient(page)
                    log.warning("Slot %d: DeepSeekClient not yet available, using ChatGPTClient stub", slot.index)
            elif Config.PROVIDER == "grok":
                from src.grok.client import GrokClient
                client = GrokClient(page)
            elif Config.PROVIDER == "mistral":
                from src.mistral.client import MistralClient
                client = MistralClient(page)
            elif Config.PROVIDER == "qwen":
                from src.qwen.client import QwenClient
                client = QwenClient(page)
            elif Config.PROVIDER == "kimi":
                from src.kimi.client import KimiClient
                client = KimiClient(page)
            else:
                from src.chatgpt.client import ChatGPTClient
                client = ChatGPTClient(page)

            slot.browser = browser
            slot.client = client
            slot.healthy = True

            # Push into the available queue
            await self._queue.put(slot)
            log.info(f"Slot {slot.index}: ready ✓")

        except Exception as e:
            log.error(f"Slot {slot.index}: failed to start — {e}")
            slot.healthy = False
            # Don't push to queue — slot stays unavailable


# ── Module-level pool instance ───────────────────────────────────

_pool: BrowserPool | None = None


def get_pool() -> BrowserPool:
    if _pool is None:
        raise RuntimeError("BrowserPool not initialized — call init_pool() first")
    return _pool


async def init_pool(size: int, provider: str) -> BrowserPool:
    """Create, start and register the global pool."""
    global _pool
    _pool = BrowserPool(size=size, provider=provider)
    await _pool.start()
    return _pool


async def close_pool() -> None:
    """Close the global pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
