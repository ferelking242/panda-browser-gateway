#!/usr/bin/env bash
# ── Panda Gateway — All-in-one startup ─────────────────────────────
# Lance : Xvfb → x11vnc → noVNC (port 6080) → API Gateway (port 8000)
# Le browser est accessible via Dashboard > Browser (iframe /vnc/vnc.html)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DISPLAY_NUM=99
VNC_PORT=5900
NOVNC_PORT=6080
VNC_PASS="${VNC_PASSWORD:-pandagw}"

# ── Hardcode Nix store paths (not in default PATH) ──────────────────
WEBSOCKIFY_BIN="/nix/store/031kfpijr04xpfkps46n3qhqinapw5bi-python3.11-websockify-0.12.0/bin/websockify"
NOVNC_SHARE="/nix/store/0a18wyirbc3ls9yvlw33lrmql94n2hmc-novnc-1.5.0/share/webapps/novnc"
XVFB_BIN="/nix/store/ykck7gdd6szwrb3qnpb5y5fvjlnmzhz0-xorg-server-21.1.18/bin/Xvfb"
X11VNC_BIN="/nix/store/4rxi8q5x6yb39ykygl5ddvmlx6v26gjy-x11vnc-0.9.17/bin/x11vnc"
NC_BIN="$(which nc 2>/dev/null || echo nc)"
SYSTEM_CHROME="/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Panda Gateway — Démarrage complet                  ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  API Gateway  → :8000                               ║"
echo "║  noVNC        → :6080 (iframe dans le dashboard)   ║"
echo "╚══════════════════════════════════════════════════════╝"

# ── Nettoyage idempotent ─────────────────────────────────────────
rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}" 2>/dev/null || true
pkill -f "Xvfb.*:${DISPLAY_NUM}"       2>/dev/null || true
pkill -f "x11vnc.*${VNC_PORT}"         2>/dev/null || true
pkill -f "novnc.*${NOVNC_PORT}"        2>/dev/null || true
pkill -f "websockify.*${NOVNC_PORT}"   2>/dev/null || true
# Libérer le port API si un ancien processus le bloque
fuser -k ${NOVNC_PORT}/tcp 2>/dev/null || true
sleep 1

# ── 1. Xvfb ─────────────────────────────────────────────────────
echo "[vnc] Démarrage Xvfb :${DISPLAY_NUM}..."
nohup "$XVFB_BIN" ":${DISPLAY_NUM}" -screen 0 1280x800x24 -ac +extension GLX +render -noreset \
  >/tmp/xvfb.log 2>&1 &
sleep 2
echo "[vnc] Xvfb démarré"

# ── 2. x11vnc ────────────────────────────────────────────────────
echo "[vnc] Démarrage x11vnc sur port ${VNC_PORT}..."
nohup "$X11VNC_BIN" \
  -display ":${DISPLAY_NUM}" \
  -rfbport "${VNC_PORT}" \
  -passwd "${VNC_PASS}" \
  -shared -forever -noxdamage -quiet \
  >/tmp/x11vnc.log 2>&1 &
sleep 1
echo "[vnc] x11vnc démarré"

# ── 3. noVNC via websockify (chemins Nix hardcodés) ──────────────
echo "[vnc] noVNC share : $NOVNC_SHARE"
echo "[vnc] Démarrage websockify sur :${NOVNC_PORT}..."
nohup "$WEBSOCKIFY_BIN" \
  --web="$NOVNC_SHARE" \
  "${NOVNC_PORT}" \
  "localhost:${VNC_PORT}" \
  >/tmp/novnc.log 2>&1 &

# Attendre que noVNC écoute
echo "[vnc] Attente noVNC sur :${NOVNC_PORT}..."
for i in $(seq 1 20); do
  if "$NC_BIN" -z 127.0.0.1 "${NOVNC_PORT}" 2>/dev/null; then
    echo "[vnc] ✅ noVNC actif sur :${NOVNC_PORT} (${i}s)"
    break
  fi
  sleep 1
done
if ! "$NC_BIN" -z 127.0.0.1 "${NOVNC_PORT}" 2>/dev/null; then
  echo "[vnc] ⚠️  noVNC pas actif après 20s"
  cat /tmp/novnc.log 2>/dev/null | tail -15
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ Stack VNC prête — Dashboard > Browser           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 4. API Gateway ───────────────────────────────────────────────
export DISPLAY=":${DISPLAY_NUM}"
export HEADLESS="${HEADLESS:-false}"
export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="$SYSTEM_CHROME"
echo "[gateway] Chromium : $SYSTEM_CHROME"

PYTHON="$(which python3 2>/dev/null || echo python3)"

echo "[gateway] Démarrage uvicorn sur :8000..."
exec "$PYTHON" -m uvicorn src.api.server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info
