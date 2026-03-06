#!/usr/bin/env bash
# Start backend and frontend for local development.
# Backend: http://127.0.0.1:8000  Frontend: http://localhost:5173
# Press Ctrl+C to stop; both processes will be terminated.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Print LAN IP so phone on same WiFi can connect (macOS: en0/en1, Linux: hostname -I)
lan_ip() {
  if command -v ipconfig &>/dev/null; then
    ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true
  elif command -v hostname &>/dev/null; then
    hostname -I 2>/dev/null | awk '{print $1}' || true
  fi
}

# Backend: ensure venv exists and deps are installed
BACKEND_DIR="$ROOT/backend"
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Backend venv not found. Creating venv and installing dependencies..."
  PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
  if [ -z "$PYTHON" ]; then
    echo "Python not found. Install Python 3.11+ and ensure python3 or python is on PATH."
    exit 1
  fi
  (cd "$BACKEND_DIR" && "$PYTHON" -m venv .venv && .venv/bin/pip install -r requirements.txt) || exit 1
  echo "Backend venv ready."
fi
# Upgrade pip in the venv (venv often ships with an old bundled pip)
echo "Upgrading pip in venv..."
(cd "$BACKEND_DIR" && .venv/bin/pip install --upgrade pip) || true
# Ensure dependencies are installed (e.g. if venv existed but packages were missing)
echo "Ensuring backend dependencies (pip install -r requirements.txt)..."
(cd "$BACKEND_DIR" && .venv/bin/pip install -r requirements.txt) || true

echo "Starting backend (http://127.0.0.1:8000) ..."
echo "  (Using real vision model: BLIP. First video upload may download ~1GB if not cached.)"
(
  cd "$BACKEND_DIR"
  exec "$BACKEND_DIR/.venv/bin/python" -m uvicorn main:app --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo "Stopping backend (PID $BACKEND_PID) ..."
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

# Wait for backend to be up
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null | grep -q 200; then
    break
  fi
  sleep 1
done
if ! curl -s -o /dev/null http://127.0.0.1:8000/health 2>/dev/null; then
  echo "Backend did not start in time. Check backend/README.md"
  kill "$BACKEND_PID" 2>/dev/null || true
  exit 1
fi
echo "Backend ready at http://127.0.0.1:8000"

LAN_IP=$(lan_ip)
if [ -n "$LAN_IP" ]; then
  echo ""
  echo "  Your IP on this network: $LAN_IP"
  echo "  On your phone (same WiFi), open: http://$LAN_IP:5173"
  echo "  (Backend API for the app: http://$LAN_IP:8000)"
  echo ""
fi

# Frontend: ensure node_modules exists
if [ ! -d "frontend/node_modules" ]; then
  echo "Frontend deps not found. Running npm install..."
  (cd frontend && npm install) || exit 1
  echo "Frontend deps ready."
fi

echo "Starting frontend (http://localhost:5173) ..."
echo "Press Ctrl+C to stop both."
cd frontend
npm run dev -- --host
