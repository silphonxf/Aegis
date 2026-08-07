#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
BACKEND_PORT="${AEGIS_BACKEND_PORT:-8000}"
MOBILE_PORT="${AEGIS_MOBILE_PORT:-5173}"
ADMIN_PORT="${AEGIS_ADMIN_PORT:-5174}"
IP_BLOCK_PORT="${AEGIS_IP_BLOCK_PORT:-18791}"

echo "📋 Port status"
ss -lntp | grep -E ":(${BACKEND_PORT}|${MOBILE_PORT}|${ADMIN_PORT}|${IP_BLOCK_PORT})\\b" || echo "No Aegis dev ports are listening."

echo
echo "🏥 Health check"
if curl -k -fsS "https://127.0.0.1:${BACKEND_PORT}/healthz" >/tmp/aegis_status_health.json 2>/dev/null; then
  cat /tmp/aegis_status_health.json
else
  echo "backend healthz unavailable"
fi

echo
echo "🔧 OpenClaw tool gateway"
if curl -k -fsS "https://127.0.0.1:${IP_BLOCK_PORT}/aegis/tools/v1/healthz" >/tmp/aegis_status_tool_gateway.json 2>/dev/null; then
  cat /tmp/aegis_status_tool_gateway.json
else
  echo "OpenClaw tool gateway unavailable"
fi

echo
echo "📄 Logs"
echo "- $LOG_DIR/backend-https.log"
echo "- $LOG_DIR/frontend-mobile.log"
echo "- $LOG_DIR/frontend-admin.log"
echo "- $LOG_DIR/frontend-ip-block.log"
