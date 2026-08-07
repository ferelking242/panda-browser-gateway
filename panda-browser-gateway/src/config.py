"""
Centralized configuration — loads from .env with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

_CODE_ROOT = Path(__file__).resolve().parent.parent
_CWD = Path.cwd()

# Prefer the invocation directory as project root when running from
# a checkout (e.g. `nix run .#proxy` from repo root). Fall back to the
# code location (used for packaged/store execution).
if (_CWD / "src").exists() and (_CWD / "scripts").exists():
    _PROJECT_ROOT = _CWD
else:
    _PROJECT_ROOT = _CODE_ROOT

# Load .env from current working directory first, then from the
# resolved project root.
load_dotenv(_CWD / ".env")
load_dotenv(_PROJECT_ROOT / ".env")


class Config:
    """All project settings in one place."""

    # Paths
    PROJECT_ROOT: Path = _PROJECT_ROOT
    BROWSER_DATA_DIR: Path = _PROJECT_ROOT / os.getenv("BROWSER_DATA_DIR", "browser_data")
    LOG_DIR: Path = _PROJECT_ROOT / os.getenv("LOG_DIR", "logs")
    IMAGES_DIR: Path = _PROJECT_ROOT / os.getenv("IMAGES_DIR", "downloads/images")

    # Browser
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"
    SLOW_MO: int = int(os.getenv("SLOW_MO", "25"))
    CHATGPT_URL: str = os.getenv("CHATGPT_URL", "https://chatgpt.com")
    CLAUDE_URL: str = os.getenv("CLAUDE_URL", "https://claude.ai")

    # Provider selection: "chatgpt", "claude", "gemini", "deepseek", "grok", "mistral", "qwen", "kimi"
    PROVIDER: str = os.getenv("PROVIDER", "chatgpt").lower()

    # Fallback provider chain (comma-separated). If primary fails, try next.
    # Example: PROVIDER_CHAIN=chatgpt,claude,gemini
    PROVIDER_CHAIN: str = os.getenv("PROVIDER_CHAIN", "")

    # Model selection
    # Default model per provider (overridable via MODEL env var or per-request)
    CHATGPT_DEFAULT_MODEL: str = os.getenv("CHATGPT_DEFAULT_MODEL", "gpt-4o")
    CLAUDE_DEFAULT_MODEL: str = os.getenv("CLAUDE_DEFAULT_MODEL", "claude-3-5-sonnet-20241022")
    GEMINI_DEFAULT_MODEL: str = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash")
    DEEPSEEK_DEFAULT_MODEL: str = os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-r1")
    GROK_DEFAULT_MODEL: str = os.getenv("GROK_DEFAULT_MODEL", "grok-3")
    MISTRAL_DEFAULT_MODEL: str = os.getenv("MISTRAL_DEFAULT_MODEL", "mistral-large")
    QWEN_DEFAULT_MODEL: str = os.getenv("QWEN_DEFAULT_MODEL", "qwen-max")
    KIMI_DEFAULT_MODEL: str = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2")

    # Additional provider URLs
    GEMINI_URL: str = os.getenv("GEMINI_URL", "https://aistudio.google.com/app/prompts/new_chat")
    DEEPSEEK_URL: str = os.getenv("DEEPSEEK_URL", "https://chat.deepseek.com")
    GROK_URL: str = os.getenv("GROK_URL", "https://grok.com")
    MISTRAL_URL: str = os.getenv("MISTRAL_URL", "https://chat.mistral.ai/chat")
    QWEN_URL: str = os.getenv("QWEN_URL", "https://chat.qwen.ai")
    KIMI_URL: str = os.getenv("KIMI_URL", "https://kimi.moonshot.cn")

    @classmethod
    def provider_url(cls) -> str:
        """Return the target URL for the active provider."""
        urls = {
            "claude": cls.CLAUDE_URL,
            "gemini": cls.GEMINI_URL,
            "deepseek": cls.DEEPSEEK_URL,
            "grok": cls.GROK_URL,
            "mistral": cls.MISTRAL_URL,
            "qwen": cls.QWEN_URL,
            "kimi": cls.KIMI_URL,
        }
        return urls.get(cls.PROVIDER, cls.CHATGPT_URL)

    @classmethod
    def default_model(cls) -> str:
        """Return the default model ID for the active provider."""
        models = {
            "claude": cls.CLAUDE_DEFAULT_MODEL,
            "gemini": cls.GEMINI_DEFAULT_MODEL,
            "deepseek": cls.DEEPSEEK_DEFAULT_MODEL,
            "grok": cls.GROK_DEFAULT_MODEL,
            "mistral": cls.MISTRAL_DEFAULT_MODEL,
            "qwen": cls.QWEN_DEFAULT_MODEL,
            "kimi": cls.KIMI_DEFAULT_MODEL,
        }
        return models.get(cls.PROVIDER, cls.CHATGPT_DEFAULT_MODEL)

    # Timeouts (ms)
    RESPONSE_TIMEOUT: int = int(os.getenv("RESPONSE_TIMEOUT", "120000"))
    SELECTOR_TIMEOUT: int = int(os.getenv("SELECTOR_TIMEOUT", "10000"))

    # Human simulation (ms)
    TYPING_SPEED_MIN: int = int(os.getenv("TYPING_SPEED_MIN", "50"))
    TYPING_SPEED_MAX: int = int(os.getenv("TYPING_SPEED_MAX", "150"))
    THINKING_PAUSE_MIN: int = int(os.getenv("THINKING_PAUSE_MIN", "500"))
    THINKING_PAUSE_MAX: int = int(os.getenv("THINKING_PAUSE_MAX", "1500"))
    # Completion poll interval — how often to check if response is ready (ms)
    POLL_INTERVAL_MS: int = int(os.getenv("POLL_INTERVAL_MS", "300"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    VERBOSE: bool = os.getenv("VERBOSE", "true").lower() == "true"

    # API (Phase 3)
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "5"))
    API_TOKEN: str = os.getenv("API_TOKEN", "")  # Bearer token for API auth (empty = no auth)

    # ── Android / multi-mode browser ──────────────────────────────────────────
    # Mode : "launch" (desktop), "cdp" (external Chrome), "android" (WebView bridge)
    BROWSER_MODE: str = os.getenv("BROWSER_MODE", "launch").lower()

    # CDP : URL du DevTools Protocol si BROWSER_MODE=cdp
    BROWSER_CDP_URL: str = os.getenv("BROWSER_CDP_URL", "")

    # Android bridge : port HTTP sur lequel Flutter écoute les commandes JS
    WEBVIEW_BRIDGE_PORT: int = int(os.getenv("WEBVIEW_BRIDGE_PORT", "9221"))

    # Multi-session browser pool
    POOL_SIZE: int = int(os.getenv("POOL_SIZE", "1"))  # 1=single browser, 3=3 parallel browsers

    # Response cache (0 = disabled)
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "0"))

    # Media pipeline
    MEDIA_BACKEND: str = os.getenv("MEDIA_BACKEND", "local")  # "local" or "hosted"
    WHISPER_API_KEY: str = os.getenv("WHISPER_API_KEY", "")
    VISION_API_KEY: str = os.getenv("VISION_API_KEY", "")
    MEDIA_MODEL_URL: str = os.getenv("MEDIA_MODEL_URL", "")
    MEDIA_MODEL_KEY: str = os.getenv("MEDIA_MODEL_KEY", "")

    # VNC
    VNC_PASSWORD: str = os.getenv("VNC_PASSWORD", "catgpt")

    # Viewport base (will be jittered ±20px)
    VIEWPORT_WIDTH: int = 1280
    VIEWPORT_HEIGHT: int = 720

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create required directories if they don't exist."""
        cls.BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
