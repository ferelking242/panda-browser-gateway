#!/usr/bin/env bash
# ── Panda Gateway — Virtual Display + noVNC ─────────────────────────────────
# Starts: Xvfb (virtual screen) → x11vnc → noVNC web UI on :6080
# Then launches the API Gateway with Chromium on that display.
#
# Access the live browser at: Dashboard > Browser tab
# or directly: http://localhost:6080/vnc.html
# VNC password: pandagw (or $VNC_PASSWORD env var)
set -e

DISPLAY_NUM=99
VNC_PORT=5900
NOVNC_PORT=6080

# Load .env first so VNC_PASSWORD can be set there
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
fi

VNC_PASS="${VNC_PASSWORD:-pandagw}"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Panda Gateway — Browser VNC                        ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  noVNC → :${NOVNC_PORT}/vnc.html                       ║"
echo "╚══════════════════════════════════════════════════════╝"

# ── Cleanup stale processes ──────────────────────────────────────
rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}" 2>/dev/null || true
pkill -f "x11vnc.*${VNC_PORT}"       2>/dev/null || true
pkill -f "websockify.*${NOVNC_PORT}" 2>/dev/null || true
pkill -f "novnc.*${NOVNC_PORT}"      2>/dev/null || true
pkill -f "Xvfb.*:${DISPLAY_NUM}"    2>/dev/null || true
fuser -k ${NOVNC_PORT}/tcp 2>/dev/null || true
sleep 1

# ── 1. Start Xvfb ───────────────────────────────────────────────
echo "[vnc] Starting Xvfb on :${DISPLAY_NUM}..."
Xvfb ":${DISPLAY_NUM}" -screen 0 1280x720x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!
echo "[vnc] Xvfb PID=$XVFB_PID"
sleep 2

# ── 2. Start x11vnc ─────────────────────────────────────────────
echo "[vnc] Starting x11vnc on port ${VNC_PORT}..."
x11vnc \
  -display ":${DISPLAY_NUM}" \
  -rfbport "${VNC_PORT}" \
  -passwd "${VNC_PASS}" \
  -shared -forever -noxdamage -xrandr -quiet -bg \
  -o /tmp/x11vnc.log 2>/dev/null
echo "[vnc] x11vnc started"
sleep 1

# ── 3. Find noVNC share dir ─────────────────────────────────────
find_novnc_share() {
  local candidates=(
    "/run/current-system/sw/share/novnc"
    "$(dirname "$(which websockify 2>/dev/null)" 2>/dev/null)/../share/novnc"
    "$(python3 -c "import websockify; import os; print(os.path.join(os.path.dirname(websockify.__file__), '..', 'share', 'novnc'))" 2>/dev/null)"
  )
  for c in "${candidates[@]}"; do
    if [ -n "$c" ] && [ -f "${c}/vnc.html" ]; then
      echo "$c"
      return 0
    fi
  done
  local novnc_bin
  novnc_bin="$(which novnc 2>/dev/null)"
  if [ -n "$novnc_bin" ]; then
    local novnc_dir
    novnc_dir="$(dirname "$novnc_bin")/.."
    for subdir in share/novnc lib/novnc; do
      if [ -f "${novnc_dir}/${subdir}/vnc.html" ]; then
        echo "${novnc_dir}/${subdir}"
        return 0
      fi
    done
  fi
  return 1
}

# ── 4. Start noVNC / websockify ─────────────────────────────────
NOVNC_SHARE="$(find_novnc_share)"

if [ -n "$NOVNC_SHARE" ] && [ -f "${NOVNC_SHARE}/vnc.html" ]; then
  echo "[vnc] noVNC share: $NOVNC_SHARE"
  echo "[vnc] Starting noVNC on port ${NOVNC_PORT}..."
  websockify --web="${NOVNC_SHARE}" "${NOVNC_PORT}" "localhost:${VNC_PORT}" &
else
  echo "[vnc] noVNC share not found — trying novnc binary..."
  NOVNC_BIN="$(which novnc 2>/dev/null)"
  if [ -n "$NOVNC_BIN" ]; then
    novnc --listen "${NOVNC_PORT}" --vnc "localhost:${VNC_PORT}" &
  else
    echo "[vnc] Starting websockify proxy only (no web UI)..."
    websockify "${NOVNC_PORT}" "localhost:${VNC_PORT}" &
  fi
fi

# Wait for noVNC to actually listen
echo "[vnc] Waiting for noVNC on :${NOVNC_PORT}..."
for i in $(seq 1 15); do
  if nc -z 127.0.0.1 "${NOVNC_PORT}" 2>/dev/null; then
    echo "[vnc] ✅ noVNC ready on :${NOVNC_PORT} (${i}s)"
    break
  fi
  sleep 1
done
if ! nc -z 127.0.0.1 "${NOVNC_PORT}" 2>/dev/null; then
  echo "[vnc] ⚠️  noVNC not yet ready after 15s"
  cat /tmp/novnc.log 2>/dev/null | tail -10 || true
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ VNC ready — Dashboard > Browser tab             ║"
echo "╚══════════════════════════════════════════════════════╝"

# ── 5. Start API Gateway on this display (non-headless) ─────────
export DISPLAY=":${DISPLAY_NUM}"
export HEADLESS=false

echo "[gateway] Launching API Gateway with DISPLAY=:${DISPLAY_NUM} (browser visible)..."

if [ -f .venv/bin/python ]; then
  exec .venv/bin/python -m uvicorn src.api.server:app \
    --host 0.0.0.0 --port 8000 --log-level info
else
  exec python -m uvicorn src.api.server:app \
    --host 0.0.0.0 --port 8000 --log-level info
fi
