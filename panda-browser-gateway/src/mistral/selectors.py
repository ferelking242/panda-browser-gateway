"""
DOM selectors for Mistral AI (chat.mistral.ai).

All selectors are lists of fallbacks tried in order.
"""

from __future__ import annotations


class MistralSelectors:
    """CSS / Playwright selectors for chat.mistral.ai."""

    # ── Chat input ──────────────────────────────────────────────
    CHAT_INPUT = [
        "textarea[placeholder*='Ask']",
        "textarea[placeholder*='message']",
        "div[contenteditable='true'][aria-label*='message']",
        "div[contenteditable='true']",
        "textarea",
    ]

    # ── Send button ──────────────────────────────────────────────
    SEND_BUTTON = [
        "button[aria-label='Send message']",
        "button[type='submit']",
        "button[data-testid='send-button']",
        "button[aria-label='Send']",
    ]

    # ── Stop button ──────────────────────────────────────────────
    STOP_BUTTON = [
        "button[aria-label='Stop']",
        "button[aria-label='Stop generating']",
        "button[aria-label='Cancel']",
    ]

    # ── Assistant message ─────────────────────────────────────────
    ASSISTANT_MESSAGE = [
        "div[data-role='assistant']",
        ".message-content.assistant",
        "[data-testid='message-assistant']",
        ".prose",
    ]

    # ── Copy button ──────────────────────────────────────────────
    COPY_BUTTON = [
        "button[aria-label='Copy']",
        "button[aria-label='Copy response']",
        "button[title='Copy']",
    ]

    # ── New chat ─────────────────────────────────────────────────
    NEW_CHAT_BUTTON = [
        "button[aria-label='New chat']",
        "a[href='/chat']",
        "button:has-text('New chat')",
        "button[data-testid='new-conversation']",
    ]

    # ── Login indicators ─────────────────────────────────────────
    LOGIN_INDICATORS = [
        "button:has-text('Sign in')",
        "a:has-text('Log in')",
        "button:has-text('Log in')",
    ]

    LOGGED_IN_INDICATORS = [
        "button[aria-label*='account']",
        "button[aria-label*='user']",
        "img[alt*='avatar']",
    ]

    # ── Model selector ───────────────────────────────────────────
    MODEL_SELECTOR = [
        "button[aria-haspopup='listbox']",
        "button[data-testid='model-selector']",
        "button:has-text('Mistral')",
        "[class*='model-select'] button",
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
