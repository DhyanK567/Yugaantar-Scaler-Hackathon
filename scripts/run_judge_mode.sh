#!/usr/bin/env bash
# MediLocker — Offline Judge Mode Launcher (Linux / macOS)
set -euo pipefail

export MEDILOCKER_MODE=judge
export MEDILOCKER_ENV=development
export MEDILOCKER_OFFLINE_MODE=true
export RAKSHA_SECRET="${RAKSHA_SECRET:-practice}"

echo "Starting MediLocker in LOCAL EVALUATION MODE (MEDILOCKER_MODE=judge, CPU-only, offline)..."
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:3001/dashboard"

python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

python3 -m http.server 3001 --bind 127.0.0.1 --directory frontend/out
