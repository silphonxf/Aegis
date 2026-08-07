#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT="${AEGIS_BACKEND_PORT:-8000}"
MOBILE_PORT="${AEGIS_MOBILE_PORT:-5173}"
ADMIN_PORT="${AEGIS_ADMIN_PORT:-5174}"
IP_BLOCK_PORT="${AEGIS_IP_BLOCK_PORT:-18791}"

pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}" || true
pkill -f "uvicorn app.main:app --reload --host 0.0.0.0 --port ${BACKEND_PORT}" || true
pkill -f "python3 -m http.server ${MOBILE_PORT}" || true
pkill -f "python3 -m http.server ${ADMIN_PORT}" || true
pkill -f "serve_https.py --host 0.0.0.0 --port ${MOBILE_PORT}" || true
pkill -f "serve_https.py --host 0.0.0.0 --port ${ADMIN_PORT}" || true
pkill -f "serve_https.py --host 0.0.0.0 --port ${IP_BLOCK_PORT}" || true

echo "🛑 Aegis local dev processes stopped (if they were running)."
