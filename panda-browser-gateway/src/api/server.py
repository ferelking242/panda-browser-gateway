"""
FastAPI server — serves ChatGPT as an API.

Launches the browser on startup, shuts it down on exit.

Usage:
    python -m src.api.server
    # or
    uvicorn src.api.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.browser.manager import BrowserManager
from src.browser.auto_login import ensure_logged_in
from src.browser.android_page import AndroidPage
from src.browser.pool import init_pool, close_pool
from src.chatgpt.client import ChatGPTClient
from src.claude.client import ClaudeClient
from src.config import Config
from src.api.routes import router, set_client
from src.api.openai_routes import openai_router, set_openai_client, set_pool, set_fallback_chain
from src.cache import init_cache
from src.api.dashboard_routes import dashboard_router
from src.log import setup_logging

log = setup_logging("api_server")


def _make_client(provider: str, page):
    """Instantiate the right client class for the given provider."""
    if provider == "claude":
        return ClaudeClient(page)
    elif provider == "gemini":
        from src.gemini.client import GeminiClient
        return GeminiClient(page)
    elif provider == "deepseek":
        from src.deepseek.client import DeepSeekClient
        return DeepSeekClient(page)
    elif provider == "grok":
        from src.grok.client import GrokClient
        return GrokClient(page)
    elif provider == "mistral":
        from src.mistral.client import MistralClient
        return MistralClient(page)
    elif provider == "qwen":
        from src.qwen.client import QwenClient
        return QwenClient(page)
    elif provider == "kimi":
        from src.kimi.client import KimiClient
        return KimiClient(page)
    else:
        return ChatGPTClient(page)


# Global instances — needed for lifespan
_browser: BrowserManager | None = None
_client: ChatGPTClient | ClaudeClient | None = None

# Fallback pools — keyed by provider name, closed on shutdown
_fallback_pools: list = []


async def _setup_fallback_chain(mode: str, primary_provider: str) -> None:
    """
    If PROVIDER_CHAIN is configured, spin up lightweight single-browser pools
    for each fallback provider and register them in openai_routes.

    PROVIDER_CHAIN=chatgpt,claude,gemini
    Primary is always Config.PROVIDER — only the *other* providers are fallbacks.
    """
    global _fallback_pools

    chain_str = Config.PROVIDER_CHAIN.strip()
    if not chain_str:
        return

    all_providers = [p.strip().lower() for p in chain_str.split(",")]
    # Remove primary — it's already running
    fallback_providers = [p for p in all_providers if p != primary_provider]
    if not fallback_providers:
        return

    log.info(f"Fallback chain: initializing providers {fallback_providers}")
    chain_entries: list[tuple[str, object]] = []

    for fb_provider in fallback_providers:
        try:
            fb_pool = await init_pool(size=1, provider=fb_provider)
            _fallback_pools.append(fb_pool)
            chain_entries.append((fb_provider, fb_pool))
            log.info(f"Fallback provider ready: {fb_provider}")
        except Exception as e:
            log.warning(f"Fallback provider {fb_provider} failed to start: {e} — skipped")

    if chain_entries:
        set_fallback_chain(chain_entries)
        log.info(f"Fallback chain active with {len(chain_entries)} provider(s)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: initialise le navigateur selon BROWSER_MODE.

    Modes :
      - launch  (défaut) : Patchright lance Chromium localement
      - cdp              : connexion à un Chrome existant via DevTools Protocol
      - android          : AndroidPage — bridge HTTP vers Flutter WebView
    """
    global _browser, _client

    mode = Config.BROWSER_MODE
    _provider_names = {
        "claude": "Claude",
        "gemini": "Gemini AI Studio",
        "deepseek": "DeepSeek",
        "grok": "Grok",
        "mistral": "Mistral AI",
        "qwen": "Qwen",
        "kimi": "Kimi",
    }
    provider_name = _provider_names.get(Config.PROVIDER, "ChatGPT")
    target_url = Config.provider_url()

    # ── Init response cache ──────────────────────────────────────
    init_cache()

    log.info(f"Starting gateway — mode={mode}, provider={provider_name}")

    if mode == "android":
        # ── Mode Android : bridge vers la WebView Flutter ─────────────────
        log.info(f"Android mode — WebView bridge on port {Config.WEBVIEW_BRIDGE_PORT}")
        page = AndroidPage(bridge_port=Config.WEBVIEW_BRIDGE_PORT)

        # Naviguer vers le provider dans la WebView
        log.info(f"Navigating WebView to {target_url}")
        try:
            await page.goto(target_url)
        except Exception as e:
            log.warning(f"Initial navigation failed (WebView may not be ready): {e}")
            log.info("Gateway starting anyway — connect via the panda-ide Gateway panel")

        _client = _make_client(Config.PROVIDER, page)  # type: ignore[arg-type]
        _browser = None  # Pas de BrowserManager en mode android

        set_client(_client, None)  # type: ignore[arg-type]
        set_openai_client(_client)
        log.info(f"API server ready — Android/WebView mode, provider={provider_name}")

        yield

        await page.close()
        log.info("AndroidPage closed")

    elif mode == "cdp":
        # ── Mode CDP : connexion à un Chrome externe ──────────────────────
        cdp_url = Config.BROWSER_CDP_URL
        if not cdp_url:
            raise ValueError(
                "BROWSER_MODE=cdp requires BROWSER_CDP_URL "
                "(e.g. http://127.0.0.1:9222)"
            )
        log.info(f"CDP mode — connecting to {cdp_url}")
        _browser = BrowserManager()
        page = await _browser.start_cdp(cdp_url)

        await _browser.apply_stealth_patches()

        _client = _make_client(Config.PROVIDER, page)

        set_client(_client, _browser)
        set_openai_client(_client)
        log.info(f"API server ready — CDP mode, provider={provider_name}")

        yield

        log.info("Shutting down — disconnecting CDP browser...")
        await _browser.close()
        log.info("Browser disconnected")

    else:
        # ── Mode launch (défaut) : Patchright lance Chromium ─────────────
        pool_size = Config.POOL_SIZE

        if pool_size > 1:
            # ── Pool mode: N browsers en parallèle ───────────────────────
            log.info(f"Launch mode — pool of {pool_size} browsers (provider={provider_name})")
            pool = await init_pool(size=pool_size, provider=Config.PROVIDER)
            set_pool(pool)

            # For legacy routes (dashboard_routes, routes.py) inject the first slot's client
            # Pool slots expose their client via the queue; grab one for registration only
            first_slot = pool._slots[0]
            if first_slot.client:
                set_client(first_slot.client, first_slot.browser)
                set_openai_client(first_slot.client)

            # ── Fallback chain (if configured) ───────────────────────────
            await _setup_fallback_chain(mode="pool", primary_provider=Config.PROVIDER)

            log.info(f"API server ready — {pool_size} browsers pooled, provider={provider_name}")

            yield  # Server is running

            log.info("Shutting down pool...")
            await close_pool()
            # Close fallback pools
            for fb_pool in _fallback_pools:
                try:
                    await fb_pool.close()
                except Exception:
                    pass
            log.info("Pool closed")

        else:
            # ── Single browser mode (default, POOL_SIZE=1) ────────────────
            log.info("Launch mode — single browser (provider={})".format(provider_name))
            _browser = BrowserManager()
            page = await _browser.start()

            log.info(f"Provider: {provider_name} ({target_url})")

            # Navigate with retries (DNS can be slow in Docker)
            max_retries = 5
            for attempt in range(1, max_retries + 1):
                try:
                    log.info(f"Navigation attempt {attempt}/{max_retries} to {target_url}")
                    await _browser.navigate(target_url)
                    break
                except Exception as e:
                    log.warning(f"Navigation attempt {attempt} failed: {e}")
                    if attempt == max_retries:
                        log.error("All navigation attempts failed")
                        raise
                    wait_time = attempt * 5  # 5s, 10s, 15s, 20s
                    log.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

            # Apply stealth patches AFTER the first navigation.
            # In Docker, applying stealth init scripts before navigation
            # causes Chrome's DNS resolver to fail (ERR_NAME_NOT_RESOLVED).
            await _browser.apply_stealth_patches()

            await asyncio.sleep(3)

            logged_in = await _browser.is_logged_in()
            if not logged_in:
                log.warning(
                    f"Not logged in to {provider_name}. "
                    "Open the browser (VNC or headless=false) and sign in manually. "
                    "The API server is starting anyway — requests will fail until you're logged in."
                )
            else:
                log.info(f"Already logged in to {provider_name}")

            _client = _make_client(Config.PROVIDER, page)

            set_client(_client, _browser)
            set_openai_client(_client)

            # ── Fallback chain (if configured) ───────────────────────────
            await _setup_fallback_chain(mode="single", primary_provider=Config.PROVIDER)

            log.info(f"API server ready — browser launched, logged in to {provider_name}")

            yield  # Server is running

            log.info("Shutting down — closing browser...")
            await _browser.close()
            log.info("Browser closed")


app = FastAPI(
    title="CatGPT Gateway API",
    description=(
        "Browser automation API for ChatGPT and Claude. "
        "Sends messages via browser and returns responses."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Bearer Token Auth Middleware ────────────────────────────────
class BearerTokenMiddleware:
    """
    Pure ASGI middleware for Bearer token auth.

    Uses raw ASGI protocol instead of BaseHTTPMiddleware to avoid the
    Python 3.9 event-loop mismatch bug that corrupts asyncio.Lock
    when exceptions propagate through BaseHTTPMiddleware's task group.

    Skips auth for /docs, /openapi.json, and health-check paths.
    """

    OPEN_PATHS = {b"/docs", b"/redoc", b"/openapi.json", b"/healthz", b"/client", b"/client.html"}

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Let CORS preflight pass through without auth
        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        token = Config.API_TOKEN
        if not token:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "").encode() if isinstance(scope.get("path"), str) else scope.get("raw_path", b"")
        # Also check the string path for comparison
        path_str = scope.get("path", "")
        if path_str in {"/docs", "/redoc", "/openapi.json", "/healthz"}:
            await self.app(scope, receive, send)
            return

        # Extract headers
        headers = dict(scope.get("headers", []))

        # 1. Check Authorization: Bearer <token>
        auth_value = headers.get(b"authorization", b"").decode()
        provided = ""
        if auth_value.startswith("Bearer "):
            provided = auth_value[7:]

        # 2. Fallback: check Cookie: api_token=<token>
        if not provided:
            cookie_header = headers.get(b"cookie", b"").decode()
            for part in cookie_header.split(";"):
                part = part.strip()
                if part.startswith("api_token="):
                    provided = part[len("api_token="):]
                    break

        if provided != token:
            response = JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "message": (
                            "Invalid or missing API token. "
                            "Use Authorization: Bearer <API_TOKEN> header "
                            "or api_token=<API_TOKEN> cookie."
                        ),
                        "type": "auth_error",
                    }
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


app.add_middleware(BearerTokenMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(openai_router)
app.include_router(dashboard_router)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Unauthenticated health-check for Docker / load-balancers."""
    return {"status": "ok"}


@app.get("/client", include_in_schema=False, response_class=HTMLResponse)
async def test_client():
    """HTML test client — no auth required."""
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🐼 Panda Gateway — Test</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d0d0d;color:#e8e8e8;height:100dvh;display:flex;flex-direction:column}
  header{padding:14px 20px;background:#111;border-bottom:1px solid #222;display:flex;align-items:center;gap:10px;flex-shrink:0}
  header h1{font-size:16px;font-weight:600}
  .badge{font-size:11px;padding:2px 8px;border-radius:999px;background:#1a1a1a;border:1px solid #333;color:#888}
  .badge.ok{border-color:#22c55e44;color:#22c55e;background:#22c55e11}
  .badge.err{border-color:#ef444444;color:#ef4444;background:#ef444411}
  #cfg{background:#111;border-bottom:1px solid #222;padding:10px 20px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;flex-shrink:0}
  #cfg label{font-size:11px;color:#666}
  #cfg input{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;color:#e8e8e8;padding:5px 10px;font-size:12px;font-family:monospace;outline:none}
  #cfg input.url{width:min(340px,100%)}
  #cfg input.tok{width:min(260px,100%)}
  #cfg select{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;color:#e8e8e8;padding:5px 8px;font-size:12px;outline:none}
  #msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px}
  .m{max-width:80%;padding:12px 16px;border-radius:12px;font-size:14px;line-height:1.6;white-space:pre-wrap;word-break:break-word}
  .m.user{align-self:flex-end;background:#1d4ed8;border-bottom-right-radius:3px}
  .m.assistant{align-self:flex-start;background:#1a1a1a;border:1px solid #2a2a2a;border-bottom-left-radius:3px}
  .m.sys{align-self:center;background:transparent;border:1px solid #222;color:#555;font-size:12px;padding:6px 14px}
  .m.err{align-self:center;background:#ef444411;border:1px solid #ef444433;color:#ef4444;font-size:12px;max-width:90%}
  .dim{opacity:.4;font-style:italic}
  #foot{padding:14px 20px;background:#111;border-top:1px solid #222;display:flex;gap:8px;align-items:flex-end;flex-shrink:0}
  textarea{flex:1;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;color:#e8e8e8;padding:10px 14px;font-size:14px;font-family:inherit;resize:none;outline:none;min-height:42px;max-height:120px;line-height:1.5}
  button{cursor:pointer;border:none;border-radius:10px;font-size:14px;font-weight:600;height:42px;padding:0 18px}
  #bsend{background:#1d4ed8;color:#fff}
  #bsend:hover{background:#2563eb}
  #bsend:disabled{background:#222;color:#555;cursor:default}
  #bclr{background:transparent;border:1px solid #2a2a2a;color:#666;padding:0 12px;font-size:12px}
  .pbtn{background:#1a1a1a;border:1px solid #2a2a2a;color:#888;height:32px;padding:0 12px;font-size:12px;font-weight:400}
</style>
</head>
<body>
<header>
  <span style="font-size:22px">🐼</span>
  <h1>Panda Gateway</h1>
  <span class="badge" id="st">—</span>
</header>
<div id="cfg">
  <label>API URL</label>
  <input id="url" class="url" value=""/>
  <label>Token</label>
  <input id="tok" class="tok" value="6dcbf607612135373f7270370e54325a7f1430a55395066c"/>
  <label>Modèle</label>
  <select id="mdl"><option>gpt-4o</option><option>gpt-4o-mini</option><option>gpt-4-turbo</option><option>gpt-3.5-turbo</option></select>
  <button class="pbtn" onclick="ping()">Ping</button>
</div>
<div id="msgs"><div class="m sys">Prêt — clique Ping pour tester la connexion.</div></div>
<div id="foot">
  <textarea id="ta" placeholder="Message…" rows="1"></textarea>
  <button id="bclr" onclick="clear_()">🗑</button>
  <button id="bsend" onclick="send()">Envoyer</button>
</div>
<script>
// Auto-detect: same host, same port
document.getElementById('url').value = window.location.origin;

const hist=[];
const msgs=document.getElementById('msgs');
const g=id=>document.getElementById(id);
const cfg=()=>({url:g('url').value.replace(/\\/$/,''),tok:g('tok').value.trim(),mdl:g('mdl').value});
function add(role,txt,cls=''){const d=document.createElement('div');d.className='m '+role+' '+cls;d.textContent=txt;msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;return d}
function status(t,c=''){const e=g('st');e.textContent=t;e.className='badge '+c}

async function ping(){
  status('ping…');const{url,tok}=cfg();
  try{
    const r=await fetch(url+'/healthz');
    if(r.ok){status('✓ connecté','ok');add('sys','✓ Gateway en ligne')}
    else{status('✗ '+r.status,'err');add('err','HTTP '+r.status)}
  }catch(e){status('✗ offline','err');add('err','Connexion impossible: '+e.message)}
}

async function send(){
  const ta=g('ta');const txt=ta.value.trim();if(!txt)return;
  const{url,tok,mdl}=cfg();
  ta.value='';ta.style.height='';g('bsend').disabled=true;
  hist.push({role:'user',content:txt});add('user',txt);
  const th=add('assistant','…','dim');
  try{
    status('envoi…');
    const r=await fetch(url+'/v1/chat/completions',{
      method:'POST',
      headers:{'Authorization':'Bearer '+tok,'Content-Type':'application/json'},
      body:JSON.stringify({model:mdl,messages:hist,stream:false})
    });
    if(!r.ok){const t=await r.text();th.remove();add('err','Erreur '+r.status+': '+t);status('✗ '+r.status,'err');hist.pop();return}
    const d=await r.json();
    const rep=d.choices?.[0]?.message?.content??JSON.stringify(d);
    hist.push({role:'assistant',content:rep});
    th.textContent=rep;th.className='m assistant';status('✓ ok','ok');
  }catch(e){th.remove();add('err','Erreur réseau: '+e.message);status('✗ err','err');hist.pop()}
  finally{g('bsend').disabled=false;ta.focus()}
}

function clear_(){hist.length=0;msgs.innerHTML='<div class="m sys">Conversation effacée.</div>'}
g('ta').addEventListener('input',function(){this.style.height='auto';this.style.height=Math.min(this.scrollHeight,120)+'px'});
g('ta').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});
ping();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/client.html", include_in_schema=False, response_class=HTMLResponse)
async def test_client_html():
    return await test_client()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.server:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        log_level="info",
    )
