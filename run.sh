#!/usr/bin/env bash
# Starts the DCF dashboard: FastAPI backend (8000) + Vite frontend (5173).
# Usage: ./run.sh   then open http://localhost:5173
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d backend/.venv ]; then
  echo "Creating Python venv and installing backend dependencies..."
  python -m venv backend/.venv
  backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt 2>/dev/null \
    || backend/.venv/bin/python -m pip install -r backend/requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend dependencies..."
  npm --prefix frontend install
fi

PY=backend/.venv/Scripts/python.exe
[ -f "$PY" ] || PY=backend/.venv/bin/python

echo "Starting backend on http://localhost:8000 ..."
(cd backend && exec "$(pwd)/.venv/Scripts/python.exe" -m uvicorn app.main:app --port 8000 2>/dev/null \
  || exec "$(pwd)/.venv/bin/python" -m uvicorn app.main:app --port 8000) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

echo "Starting frontend on http://localhost:5173 ... (Ctrl+C stops both)"
npm --prefix frontend run dev
