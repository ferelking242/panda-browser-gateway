"""
DOM selectors for Kimi (kimi.moonshot.cn).

All selectors are lists of fallbacks tried in order.
"""

from __future__ import annotations


class KimiSelectors:
    """CSS / Playwright selectors for kimi.moonshot.cn."""

    # ── Chat input ──────────────────────────────────────────────
    CHAT_INPUT = [
        "div[contenteditable='true'][data-testid='chat-input']",
        "div[contenteditable='true'][placeholder*='message']",
        "textarea[placeholder*='message']",
        "div[contenteditable='true']",
        "textarea",
    ]

    # ── Send button ──────────────────────────────────────────────
    SEND_BUTTON = [
        "button[data-testid='send-button']",
        "button[aria-label='Send']",
        "button[type='submit']",
        "div[role='button'][aria-label*='send']",
    ]

    # ── Stop button ──────────────────────────────────────────────
    STOP_BUTTON = [
        "button[aria-label='Stop']",
        "button[aria-label='Stop generating']",
        "button[data-testid='stop-button']",
    ]

    # ── Assistant message ─────────────────────────────────────────
    ASSISTANT_MESSAGE = [
        "div[data-role='assistant']",
        ".kimi-message.assistant",
        ".message-content",
        ".markdown-body",
    ]

    # ── Copy button ──────────────────────────────────────────────
    COPY_BUTTON = [
        "button[aria-label='Copy']",
        "button[title='Copy']",
        "button[data-testid='copy-button']",
    ]

    # ── New chat ─────────────────────────────────────────────────
    NEW_CHAT_BUTTON = [
        "button[aria-label='New chat']",
        "a[href='/']",
        "button[data-testid='new-chat']",
        "button:has-text('New chat')",
    ]

    # ── Login indicators ─────────────────────────────────────────
    LOGIN_INDICATORS = [
        "button:has-text('Sign in')",
        "a:has-text('Log in')",
        "button:has-text('Login')",
    ]

    LOGGED_IN_INDICATORS = [
        "img[alt*='avatar']",
        ".user-avatar",
        "button[aria-label*='account']",
    ]

    # ── Model selector ───────────────────────────────────────────
    MODEL_SELECTOR = [
        "button[aria-haspopup='listbox']",
        "button[data-testid='model-selector']",
        "button:has-text('Kimi')",
        ".model-select button",
    ]

    # ── File upload ──────────────────────────────────────────────
    FILE_UPLOAD_INPUT = [
        "input[type='file']",
    ]

    # ── Sidebar threads ──────────────────────────────────────────
    SIDEBAR_THREAD_LINKS = [
        "a[href*='/chat/']",
        "li[data-conversation-id] a",
    ]
