"""
DOM selectors for Grok (grok.com).

All selectors are lists of fallbacks tried in order.
"""

from __future__ import annotations


class GrokSelectors:
    """CSS / Playwright selectors for grok.com."""

    # ── Chat input ──────────────────────────────────────────────
    CHAT_INPUT = [
        "textarea[placeholder*='Ask']",
        "textarea[data-testid='grok-input']",
        "div[contenteditable='true'][aria-label*='message']",
        "textarea[placeholder*='message']",
        "div[contenteditable='true']",
        "textarea",
    ]

    # ── Send button ──────────────────────────────────────────────
    SEND_BUTTON = [
        "button[aria-label='Send']",
        "button[data-testid='send-button']",
        "button[type='submit']",
        "button[aria-label='Submit']",
    ]

    # ── Stop button ──────────────────────────────────────────────
    STOP_BUTTON = [
        "button[aria-label='Stop']",
        "button[aria-label='Stop generating']",
        "button[data-testid='stop-button']",
    ]

    # ── Assistant message ─────────────────────────────────────────
    ASSISTANT_MESSAGE = [
        "div[data-message-author-role='assistant']",
        ".message-bubble.assistant",
        "div[data-testid='message-assistant']",
        ".prose",
    ]

    # ── Copy button ──────────────────────────────────────────────
    COPY_BUTTON = [
        "button[aria-label='Copy']",
        "button[aria-label='Copy response']",
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
        "a:has-text('Sign in')",
        "button:has-text('Log in')",
    ]

    LOGGED_IN_INDICATORS = [
        "button[aria-label*='account']",
        "button[aria-label*='profile']",
        "img[alt*='avatar']",
    ]

    # ── Model selector ───────────────────────────────────────────
    MODEL_SELECTOR = [
        "button[aria-label*='model']",
        "button[data-testid='model-selector']",
        "button:has-text('Grok')",
    ]

    # ── File upload ──────────────────────────────────────────────
    FILE_UPLOAD_INPUT = [
        "input[type='file']",
    ]

    # ── Sidebar threads ──────────────────────────────────────────
    SIDEBAR_THREAD_LINKS = [
        "a[href*='/chat/']",
        "nav a[href*='conversation']",
    ]
