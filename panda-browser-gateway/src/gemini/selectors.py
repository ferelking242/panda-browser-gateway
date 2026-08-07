"""
DOM selectors for Google AI Studio (aistudio.google.com).

All selectors are lists of fallbacks tried in order.
When Google updates their UI, only this file needs changing.
"""

from __future__ import annotations


class GeminiSelectors:
    """CSS / Playwright selectors for AI Studio UI elements."""

    # ── Chat input ──────────────────────────────────────────────
    CHAT_INPUT = [
        "rich-textarea .ql-editor",
        "ms-prompt-input-wrapper rich-textarea .ql-editor",
        "div[contenteditable='true'].ql-editor",
        "textarea[placeholder*='message']",
        "div[contenteditable='true']",
    ]

    # ── Send / Run button ────────────────────────────────────────
    SEND_BUTTON = [
        "button[aria-label='Run']",
        "button[mattooltip='Run']",
        "run-button button",
        "button.run-button",
        "button[aria-label='Send message']",
        "button:has-text('Run')",
    ]

    # ── Stop button (while streaming) ───────────────────────────
    STOP_BUTTON = [
        "button[aria-label='Stop']",
        "button[mattooltip='Stop']",
    ]

    # ── Assistant response ───────────────────────────────────────
    # AI Studio wraps model outputs in ms-chat-turn or similar components
    ASSISTANT_MESSAGE = [
        "ms-chat-turn[role='model']",
        "ms-chat-turn .model-response-text",
        ".model-response-text",
        "ms-model-response",
        "[data-role='model']",
    ]

    # ── Copy button (appears on completed response) ─────────────
    COPY_BUTTON = [
        "button[aria-label='Copy response']",
        "button[aria-label='Copy']",
        "button[mattooltip='Copy']",
        "ms-copy-button button",
    ]

    # ── New chat / reset ─────────────────────────────────────────
    NEW_CHAT_BUTTON = [
        "button[aria-label='New chat']",
        "a[href*='/new_chat']",
        "button:has-text('New chat')",
    ]

    # ── Model selector ───────────────────────────────────────────
    MODEL_SELECTOR = [
        "ms-model-selector button",
        "button[aria-label='Select model']",
        "mat-select[aria-label='Model']",
    ]

    # ── Login indicators ─────────────────────────────────────────
    LOGIN_INDICATORS = [
        "button:has-text('Sign in')",
        "a:has-text('Sign in')",
    ]

    LOGGED_IN_INDICATORS = [
        "img[alt='Google Account']",
        "button[aria-label*='account']",
    ]

    # ── File upload ──────────────────────────────────────────────
    FILE_UPLOAD_INPUT = [
        "input[type='file']",
    ]
