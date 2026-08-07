"""
DOM selectors for DeepSeek (chat.deepseek.com).

All selectors are lists of fallbacks tried in order.
"""

from __future__ import annotations


class DeepSeekSelectors:
    """CSS / Playwright selectors for chat.deepseek.com."""

    # ── Chat input ──────────────────────────────────────────────
    CHAT_INPUT = [
        "textarea#chat-input",
        "textarea[placeholder*='message']",
        "div[contenteditable='true']",
        "textarea",
    ]

    # ── Send button ──────────────────────────────────────────────
    SEND_BUTTON = [
        "button[aria-label='Send message']",
        "button[type='submit']",
        "div[role='button'][aria-label='Send']",
        "#send-button",
    ]

    # ── Stop button ──────────────────────────────────────────────
    STOP_BUTTON = [
        "button[aria-label='Stop']",
        "button[aria-label='Stop generating']",
    ]

    # ── Assistant message ─────────────────────────────────────────
    ASSISTANT_MESSAGE = [
        "div[data-role='assistant']",
        ".ds-message.assistant-message",
        ".message-content[data-role='assistant']",
        ".markdown-body",
    ]

    # ── Copy button ──────────────────────────────────────────────
    COPY_BUTTON = [
        "button[aria-label='Copy']",
        "button[title='Copy']",
    ]

    # ── New chat ─────────────────────────────────────────────────
    NEW_CHAT_BUTTON = [
        "button[aria-label='New chat']",
        "a[href='/']",
        "button:has-text('New chat')",
    ]

    # ── Sidebar threads ──────────────────────────────────────────
    SIDEBAR_THREAD_LINKS = [
        "a[href^='/chat/']",
        "nav a[href*='chat']",
    ]

    # ── Login indicators ─────────────────────────────────────────
    LOGIN_INDICATORS = [
        "button:has-text('Sign in')",
        "a:has-text('Log in')",
    ]

    LOGGED_IN_INDICATORS = [
        "button[aria-label='User menu']",
        ".user-avatar",
    ]

    # ── Model selector ───────────────────────────────────────────
    MODEL_SELECTOR = [
        "button[class*='model-select']",
        "button:has-text('DeepSeek')",
    ]

    # ── File upload ──────────────────────────────────────────────
    FILE_UPLOAD_INPUT = [
        "input[type='file']",
    ]
