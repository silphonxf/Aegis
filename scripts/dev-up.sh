#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="$ROOT_DIR/deploy"
BACKEND_DIR="$ROOT_DIR/backend"
MOBILE_DIR="$ROOT_DIR/frontend-mobile"
ADMIN_DIR="$ROOT_DIR/frontend-admin"
LOG_DIR="$ROOT_DIR/.logs"
mkdir -p "$LOG_DIR"

get_lan_ips() {
  hostname -I 2>/dev/null | awk '{for(i=1;i<=NF;i++) print $i}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || true
}

print_access_urls() {
  local ips
  ips="$(get_lan_ips)"

  echo
  echo "🚀 Aegis services are up. Access URLs:"
  echo "- Backend API:    http://127.0.0.1:8000"
  echo "- Admin Frontend: http://127.0.0.1:5174"
  echo "- Mobile Frontend:http://127.0.0.1:5173"

  if [[ -n "$ips" ]]; then
    while IFS= read -r ip; do
      [[ -z "$ip" ]] && continue
      echo "- Backend API (LAN):    http://$ip:8000"
      echo "- Admin Frontend (LAN): http://$ip:5174"
      echo "- Mobile Frontend (LAN):http://$ip:5173"
    done <<< "$ips"
  fi

  echo
  echo "💡 登录建议：前端 API 地址填当前页面主机的 :8000，例如 http://<当前IP>:8000"
  echo
}

stop_local_processes() {
  pkill -f "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" || true
  pkill -f "python3 -m http.server 5173" || true
  pkill -f "python3 -m http.server 5174" || true
}

start_local_processes() {
  stop_local_processes

  nohup bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" > "$LOG_DIR/backend.log" 2>&1 &
  nohup bash -lc "cd '$MOBILE_DIR' && python3 -m http.server 5173" > "$LOG_DIR/frontend-mobile.log" 2>&1 &
  nohup bash -lc "cd '$ADMIN_DIR' && python3 -m http.server 5174" > "$LOG_DIR/frontend-admin.log" 2>&1 &

  sleep 1
  echo "📋 Local dev process status:"
  ss -lntp | grep -E ':(8000|5173|5174)\b' || true
}

if docker compose version >/dev/null 2>&1; then
  cd "$DEPLOY_DIR"
  docker compose up -d --build
  print_access_urls
  echo "📋 Container status:"
  docker compose ps
else
  echo "ℹ️ docker compose 不可用，自动切换到本地开发模式（uvicorn + http.server）。"
  start_local_processes
  print_access_urls
  echo "📄 Logs:"
  echo "- $LOG_DIR/backend.log"
  echo "- $LOG_DIR/frontend-mobile.log"
  echo "- $LOG_DIR/frontend-admin.log"
fi
