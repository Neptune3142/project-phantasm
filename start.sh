#!/usr/bin/env bash
# =============================================================================
# Project Phantasm — one-shot launcher
#
#   ./start.sh          # backend + frontend (simulation mode)
#   ./start.sh --live   # backend + frontend (live mode)
#   ./start.sh --n8n    # also spin up n8n via docker compose
#
# Backend:  http://localhost:8100
# Frontend: http://localhost:5173
# n8n:      http://localhost:5679  (only with --n8n)
# =============================================================================
set -e

cd "$(dirname "$0")"

LIVE_MODE=0
INCLUDE_N8N=0
for arg in "$@"; do
  case "$arg" in
    --live) LIVE_MODE=1 ;;
    --n8n)  INCLUDE_N8N=1 ;;
    *) echo "Unknown arg: $arg" ;;
  esac
done

# --- 1. Backend setup --------------------------------------------------------
cd backend

# Create .env from .env.example if missing.
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[start] Created backend/.env from .env.example"
fi

# Switch mode if requested.
if [ "$LIVE_MODE" -eq 1 ]; then
  if grep -q "^SIMULATION_MODE=" .env; then
    sed -i.bak 's/^SIMULATION_MODE=.*/SIMULATION_MODE=false/' .env
  else
    echo "SIMULATION_MODE=false" >> .env
  fi
  echo "[start] SIMULATION_MODE=false (LIVE mode)"
else
  if grep -q "^SIMULATION_MODE=" .env; then
    sed -i.bak 's/^SIMULATION_MODE=.*/SIMULATION_MODE=true/' .env
  else
    echo "SIMULATION_MODE=true" >> .env
  fi
  echo "[start] SIMULATION_MODE=true (simulation mode)"
fi

# Python deps
if [ -f requirements.txt ]; then
  pip install -q -r requirements.txt 2>&1 | tail -2
fi

# Launch backend on port 8100
echo "[start] Launching FastAPI backend on http://localhost:8100"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload &
BACKEND_PID=$!

# --- 2. Frontend setup -------------------------------------------------------
cd ../frontend
if [ ! -d node_modules ]; then
  echo "[start] Installing frontend dependencies…"
  npm install --silent
fi

echo "[start] Launching Vite frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

# --- 3. n8n (optional) ------------------------------------------------------
if [ "$INCLUDE_N8N" -eq 1 ]; then
  cd ..
  if command -v docker >/dev/null 2>&1; then
    echo "[start] Launching n8n on http://localhost:5679 via docker compose"
    docker compose up -d n8n
  else
    echo "[start] docker not available — skipping n8n. Install Docker Desktop to use n8n."
  fi
fi

# --- 4. Trap and shutdown ----------------------------------------------------
trap "echo '[start] Shutting down…'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

echo ""
echo "============================================================"
echo "  PROJECT PHANTASM is live."
echo "    Dashboard: http://localhost:5173"
echo "    Backend:   http://localhost:8100/api/v1/health"
echo "    Mode:      $([ $LIVE_MODE -eq 1 ] && echo LIVE || echo SIMULATION)"
echo "============================================================"
echo ""

wait
