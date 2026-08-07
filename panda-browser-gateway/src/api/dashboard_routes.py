"""
Dashboard API routes — metrics, config, logs, images, threads and settings.

Endpoints:
  GET  /api/dashboard/stats                - uptime, request counts, latency
  GET  /api/dashboard/requests             - recent request log (last 100)
  GET  /api/dashboard/config               - current runtime config
  PATCH /api/dashboard/config              - update config at runtime
  GET  /api/dashboard/logs                 - tail log files (?lines=200&level=all)
  GET  /api/dashboard/images               - list generated images
  GET  /api/dashboard/threads              - recent conversation threads
  GET  /api/dashboard/cookies              - export browser cookies as JSON
  POST /api/dashboard/cookies              - import cookies into browser session
  POST /api/dashboard/token/generate       - generate a new random API token
  POST /api/dashboard/settings/reset-session - clear browser session data
"""

from __future__ import annotations

import os
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Any, List, Optional

import secrets

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# ── In-memory metrics store ──────────────────────────────────────

_start_time = time.time()

_stats: Dict[str, Any] = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_response_time_ms": 0,
}

_request_log: Deque[Dict[str, Any]] = deque(maxlen=200)


def record_request(
    endpoint: str,
    status: str,
    response_time_ms: float,
    model: str = "",
    error: str = "",
) -> None:
    """Called by routes to record a request event."""
    _stats["total_requests"] += 1
    _stats["total_response_time_ms"] += response_time_ms

    if status == "ok":
        _stats["successful_requests"] += 1
    else:
        _stats["failed_requests"] += 1

    _request_log.appendleft(
        {
            "timestamp": time.time(),
            "endpoint": endpoint,
            "status": status,
            "response_time_ms": round(response_time_ms),
            "model": model,
            "error": error,
        }
    )


# ── Schemas ──────────────────────────────────────────────────────


class StatsResponse(BaseModel):
    uptime_seconds: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    success_rate: float


class RequestEntry(BaseModel):
    timestamp: float
    endpoint: str
    status: str
    response_time_ms: int
    model: str = ""
    error: str = ""


class ConfigView(BaseModel):
    # Provider
    provider: str
    headless: bool
    slow_mo: int
    # Timeouts
    rate_limit_seconds: int
    response_timeout_ms: int
    selector_timeout_ms: int
    poll_interval_ms: int
    # Human simulation
    typing_speed_min: int
    typing_speed_max: int
    thinking_pause_min: int
    thinking_pause_max: int
    # Logging
    log_level: str
    verbose: bool
    # API
    api_host: str
    api_port: int
    api_token_set: bool


class ConfigPatch(BaseModel):
    provider: Optional[str] = None
    headless: Optional[bool] = None
    slow_mo: Optional[int] = None
    rate_limit_seconds: Optional[int] = None
    response_timeout_ms: Optional[int] = None
    selector_timeout_ms: Optional[int] = None
    poll_interval_ms: Optional[int] = None
    typing_speed_min: Optional[int] = None
    typing_speed_max: Optional[int] = None
    thinking_pause_min: Optional[int] = None
    thinking_pause_max: Optional[int] = None
    log_level: Optional[str] = None
    verbose: Optional[bool] = None
    api_token: Optional[str] = None


class LogEntry(BaseModel):
    line: str
    level: str
    timestamp: str
    logger: str
    message: str


class ImageEntry(BaseModel):
    filename: str
    size_bytes: int
    created_at: float
    url: str


class ThreadEntry(BaseModel):
    id: str
    title: str
    created_at: Optional[float] = None
    message_count: Optional[int] = None


# ── Routes ───────────────────────────────────────────────────────


@dashboard_router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    total = _stats["total_requests"]
    avg_rt = (
        _stats["total_response_time_ms"] / total if total > 0 else 0.0
    )
    success_rate = (
        _stats["successful_requests"] / total * 100 if total > 0 else 0.0
    )
    return StatsResponse(
        uptime_seconds=int(time.time() - _start_time),
        total_requests=total,
        successful_requests=_stats["successful_requests"],
        failed_requests=_stats["failed_requests"],
        avg_response_time_ms=round(avg_rt, 1),
        success_rate=round(success_rate, 1),
    )


@dashboard_router.get("/requests")
async def get_requests() -> list[RequestEntry]:
    return [RequestEntry(**r) for r in _request_log]


@dashboard_router.get("/config", response_model=ConfigView)
async def get_config() -> ConfigView:
    from src.config import Config

    return ConfigView(
        provider=Config.PROVIDER,
        headless=Config.HEADLESS,
        slow_mo=Config.SLOW_MO,
        rate_limit_seconds=Config.RATE_LIMIT_SECONDS,
        response_timeout_ms=Config.RESPONSE_TIMEOUT,
        selector_timeout_ms=Config.SELECTOR_TIMEOUT,
        poll_interval_ms=Config.POLL_INTERVAL_MS,
        typing_speed_min=Config.TYPING_SPEED_MIN,
        typing_speed_max=Config.TYPING_SPEED_MAX,
        thinking_pause_min=Config.THINKING_PAUSE_MIN,
        thinking_pause_max=Config.THINKING_PAUSE_MAX,
        log_level=Config.LOG_LEVEL,
        verbose=Config.VERBOSE,
        api_host=Config.API_HOST,
        api_port=Config.API_PORT,
        api_token_set=bool(Config.API_TOKEN),
    )


@dashboard_router.patch("/config", response_model=ConfigView)
async def patch_config(patch: ConfigPatch) -> ConfigView:
    from src.config import Config

    if patch.provider is not None and patch.provider in ("chatgpt", "claude"):
        Config.PROVIDER = patch.provider
    if patch.headless is not None:
        Config.HEADLESS = patch.headless
    if patch.slow_mo is not None:
        Config.SLOW_MO = patch.slow_mo
    if patch.rate_limit_seconds is not None:
        Config.RATE_LIMIT_SECONDS = patch.rate_limit_seconds
    if patch.response_timeout_ms is not None:
        Config.RESPONSE_TIMEOUT = patch.response_timeout_ms
    if patch.selector_timeout_ms is not None:
        Config.SELECTOR_TIMEOUT = patch.selector_timeout_ms
    if patch.poll_interval_ms is not None:
        Config.POLL_INTERVAL_MS = patch.poll_interval_ms
    if patch.typing_speed_min is not None:
        Config.TYPING_SPEED_MIN = patch.typing_speed_min
    if patch.typing_speed_max is not None:
        Config.TYPING_SPEED_MAX = patch.typing_speed_max
    if patch.thinking_pause_min is not None:
        Config.THINKING_PAUSE_MIN = patch.thinking_pause_min
    if patch.thinking_pause_max is not None:
        Config.THINKING_PAUSE_MAX = patch.thinking_pause_max
    if patch.log_level is not None and patch.log_level in ("DEBUG", "INFO", "WARNING", "ERROR"):
        Config.LOG_LEVEL = patch.log_level
    if patch.verbose is not None:
        Config.VERBOSE = patch.verbose
    if patch.api_token is not None:
        Config.API_TOKEN = patch.api_token

    return await get_config()


@dashboard_router.get("/logs")
async def get_logs(
    lines: int = Query(default=200, ge=1, le=2000),
    level: str = Query(default="all"),
) -> JSONResponse:
    """Return the last N lines from all log files, newest first."""
    from src.config import Config

    log_dir: Path = Config.LOG_DIR
    all_lines: list[dict] = []

    try:
        log_files = sorted(log_dir.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        for log_file in log_files[:5]:  # Only last 5 files
            try:
                text = log_file.read_text(errors="replace")
                for raw in reversed(text.splitlines()):
                    raw = raw.strip()
                    if not raw:
                        continue
                    # Parse standard log format: YYYY-MM-DD HH:MM:SS,mmm LEVEL logger: message
                    parts = raw.split(" ", 4)
                    detected_level = "INFO"
                    ts = ""
                    logger = log_file.stem
                    message = raw
                    if len(parts) >= 4:
                        try:
                            ts = f"{parts[0]} {parts[1]}"
                            detected_level = parts[2]
                            logger = parts[3].rstrip(":")
                            message = parts[4] if len(parts) > 4 else ""
                        except Exception:
                            pass

                    if level != "all" and detected_level.upper() != level.upper():
                        continue

                    all_lines.append({
                        "line": raw,
                        "level": detected_level,
                        "timestamp": ts,
                        "logger": logger,
                        "message": message,
                        "file": log_file.name,
                    })
                    if len(all_lines) >= lines:
                        break
            except Exception:
                continue
            if len(all_lines) >= lines:
                break
    except Exception as e:
        return JSONResponse({"error": str(e), "entries": []})

    return JSONResponse({"entries": all_lines[:lines]})


@dashboard_router.get("/images")
async def get_images() -> JSONResponse:
    """List images generated by DALL-E through the gateway."""
    from src.config import Config

    images_dir: Path = Config.IMAGES_DIR
    entries: list[dict] = []

    try:
        if images_dir.exists():
            for f in sorted(images_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                    stat = f.stat()
                    entries.append({
                        "filename": f.name,
                        "size_bytes": stat.st_size,
                        "created_at": stat.st_mtime,
                        "url": f"/api/dashboard/images/{f.name}",
                    })
    except Exception as e:
        return JSONResponse({"error": str(e), "images": []})

    return JSONResponse({"images": entries})


@dashboard_router.get("/images/{filename}")
async def serve_image(filename: str):
    """Serve a generated image file."""
    from fastapi.responses import FileResponse
    from src.config import Config

    path = Config.IMAGES_DIR / filename
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(path))


@dashboard_router.get("/threads")
async def get_threads() -> JSONResponse:
    """List recent conversation threads."""
    from src.api.routes import _client

    if _client is None:
        return JSONResponse({"threads": [], "error": "Gateway not ready"})

    try:
        threads = await _client.list_threads()
        result = []
        for t in (threads if isinstance(threads, list) else []):
            if hasattr(t, "__dict__"):
                result.append(t.__dict__)
            elif isinstance(t, dict):
                result.append(t)
        return JSONResponse({"threads": result})
    except Exception as e:
        return JSONResponse({"threads": [], "error": str(e)})


@dashboard_router.get("/cookies")
async def export_cookies() -> JSONResponse:
    """Export all browser cookies as JSON."""
    from src.api.routes import _browser
    if _browser is None or _browser.page is None:
        return JSONResponse({"ok": False, "error": "Browser not ready"}, status_code=503)
    try:
        cookies = await _browser.context.cookies()
        return JSONResponse({"ok": True, "cookies": cookies, "count": len(cookies)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


class CookiesImport(BaseModel):
    cookies: list[dict]


@dashboard_router.post("/cookies")
async def import_cookies(body: CookiesImport) -> JSONResponse:
    """Import cookies into the live browser context (no restart needed)."""
    from src.api.routes import _browser
    if _browser is None or _browser.page is None:
        return JSONResponse({"ok": False, "error": "Browser not ready"}, status_code=503)
    try:
        await _browser.context.add_cookies(body.cookies)
        # Reload the page so cookies take effect
        await _browser.page.reload(wait_until="domcontentloaded", timeout=15000)
        await _browser.page.wait_for_timeout(2000)
        logged_in = await _browser.is_logged_in()
        return JSONResponse({
            "ok": True,
            "imported": len(body.cookies),
            "logged_in": logged_in,
            "message": "Cookies importés. " + ("✅ Connecté !" if logged_in else "⚠️ Toujours pas connecté."),
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@dashboard_router.post("/token/generate")
async def generate_token() -> JSONResponse:
    """Generate a new random API token and activate it immediately."""
    from src.config import Config
    token = secrets.token_hex(24)   # 48-char hex string
    Config.API_TOKEN = token
    return JSONResponse({"ok": True, "token": token})


@dashboard_router.post("/settings/reset-session")
async def reset_session() -> JSONResponse:
    """Delete browser session data so the next start requires a fresh login."""
    from src.config import Config
    import shutil

    data_dir: Path = Config.BROWSER_DATA_DIR
    try:
        if data_dir.exists():
            shutil.rmtree(str(data_dir))
            data_dir.mkdir(parents=True, exist_ok=True)
        return JSONResponse({"ok": True, "message": "Browser session data cleared. Restart the gateway to re-login."})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
