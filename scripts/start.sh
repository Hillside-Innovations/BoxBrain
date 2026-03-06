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

# Backend
if [ ! -d "backend/.venv" ]; then
  echo "Backend venv not found. Run: cd backend && python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi

echo "Starting backend (http://127.0.0.1:8000) ..."
echo "  (Using real vision model: BLIP. First video upload may download ~1GB if not cached.)"
(
  cd backend
  . .venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port 8000
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

# Frontend
if [ ! -d "frontend/node_modules" ]; then
  echo "Frontend deps not installed. Run: cd frontend && npm install"
  exit 1
fi

echo "Starting frontend (http://localhost:5173) ..."
echo "Press Ctrl+C to stop both."
cd frontend
npm run dev -- --host
