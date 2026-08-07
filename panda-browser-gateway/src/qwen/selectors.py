"""
DOM selectors for Qwen (chat.qwen.ai — Alibaba Cloud international).

All selectors are lists of fallbacks tried in order.
"""

from __future__ import annotations


class QwenSelectors:
    """CSS / Playwright selectors for chat.qwen.ai."""

    # ── Chat input ──────────────────────────────────────────────
    CHAT_INPUT = [
        "textarea#search-input",
        "textarea[placeholder*='message']",
        "textarea[placeholder*='Ask']",
        "div[contenteditable='true']",
        "textarea",
    ]

    # ── Send button ──────────────────────────────────────────────
    SEND_BUTTON = [
        "button[aria-label='Send message']",
        "button[type='submit']",
        "#send-message-button",
        "button[aria-label='Send']",
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
        ".chat-message.assistant",
        ".message-item.assistant",
        ".markdown-body",
    ]

    # ── Copy button ──────────────────────────────────────────────
    COPY_BUTTON = [
        "button[aria-label='Copy']",
        "button[title='Copy']",
        "button[aria-label='Copy message']",
    ]

    # ── New chat ─────────────────────────────────────────────────
    NEW_CHAT_BUTTON = [
        "button[aria-label='New chat']",
        "a[href='/']",
        "button:has-text('New chat')",
        "button:has-text('New conversation')",
    ]

    # ── Login indicators ─────────────────────────────────────────
    LOGIN_INDICATORS = [
        "button:has-text('Sign in')",
        "a:has-text('Log in')",
        "button:has-text('Login')",
    ]

    LOGGED_IN_INDICATORS = [
        "button[aria-label*='user']",
        "img[alt*='avatar']",
        ".user-avatar",
    ]

    # ── Model selector ───────────────────────────────────────────
    MODEL_SELECTOR = [
        "button[aria-haspopup='listbox']",
        "button[data-testid='model-selector']",
        "button:has-text('Qwen')",
        ".model-selector button",
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
