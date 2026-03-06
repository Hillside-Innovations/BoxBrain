#!/usr/bin/env bash
# Start backend and frontend for local development.
# Backend: http://127.0.0.1:8000  Frontend: http://localhost:5173
# Press Ctrl+C to stop; both processes will be terminated.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Backend
if [ ! -d "backend/.venv" ]; then
  echo "Backend venv not found. Run: cd backend && python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi

echo "Starting backend (http://127.0.0.1:8000) ..."
(
  cd backend
  . .venv/bin/activate
  MOCK_VISION=1 uvicorn main:app --host 127.0.0.1 --port 8000
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

# Frontend
if [ ! -d "frontend/node_modules" ]; then
  echo "Frontend deps not installed. Run: cd frontend && npm install"
  exit 1
fi

echo "Starting frontend (http://localhost:5173) ..."
echo "Press Ctrl+C to stop both."
cd frontend
npm run dev
