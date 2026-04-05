#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
MOBILE_DIR="$ROOT_DIR/frontend-mobile"
ADMIN_DIR="$ROOT_DIR/frontend-admin"
DEPLOY_DIR="$ROOT_DIR/deploy"
LOG_DIR="$ROOT_DIR/.logs"
mkdir -p "$LOG_DIR"

BACKEND_PORT="${AEGIS_BACKEND_PORT:-8000}"
MOBILE_PORT="${AEGIS_MOBILE_PORT:-5173}"
ADMIN_PORT="${AEGIS_ADMIN_PORT:-5174}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOCAL_ADMIN_PASSWORD="${AEGIS_INIT_ADMIN_PASSWORD:-local_admin_pass_2026}"

get_lan_ips() {
  hostname -I 2>/dev/null | awk '{for(i=1;i<=NF;i++) print $i}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || true
}

print_access_urls() {
  local ips
  ips="$(get_lan_ips)"

  echo
  echo "🚀 Aegis services are up. Access URLs:"
  echo "- Backend API:     http://127.0.0.1:${BACKEND_PORT}"
  echo "- Admin Frontend:  http://127.0.0.1:${ADMIN_PORT}"
  echo "- Mobile Frontend: http://127.0.0.1:${MOBILE_PORT}"

  if [[ -n "$ips" ]]; then
    while IFS= read -r ip; do
      [[ -z "$ip" ]] && continue
      echo "- Backend API (LAN):     http://$ip:${BACKEND_PORT}"
      echo "- Admin Frontend (LAN):  http://$ip:${ADMIN_PORT}"
      echo "- Mobile Frontend (LAN): http://$ip:${MOBILE_PORT}"
    done <<< "$ips"
  fi

  echo
  echo "🔐 默认本地管理员: admin / ${LOCAL_ADMIN_PASSWORD}"
  echo "💡 前端 API 地址建议填当前页面主机的 :${BACKEND_PORT}"
  echo "📄 日志目录: $LOG_DIR"
  echo
}

stop_local_processes() {
  pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}" || true
  pkill -f "uvicorn app.main:app --reload --host 0.0.0.0 --port ${BACKEND_PORT}" || true
  pkill -f "python3 -m http.server ${MOBILE_PORT}" || true
  pkill -f "python3 -m http.server ${ADMIN_PORT}" || true
}

ensure_backend_env() {
  cd "$BACKEND_DIR"
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      cp .env.example .env
      python3 - <<PY
from pathlib import Path
p = Path('.env')
text = p.read_text(encoding='utf-8')
text = text.replace('change_me_to_a_long_random_secret', 'test_secret_key_for_local_dev_2026')
text = text.replace('change_me_to_a_strong_password', '${LOCAL_ADMIN_PASSWORD}')
p.write_text(text, encoding='utf-8')
PY
      echo "ℹ️ 已从 backend/.env.example 生成 backend/.env"
    else
      cat > .env <<EOF
SECRET_KEY=test_secret_key_for_local_dev_2026
INIT_ADMIN_PASSWORD=${LOCAL_ADMIN_PASSWORD}
DATABASE_URL=sqlite:///./aegis.db
APP_ENV=dev
EOF
      echo "ℹ️ 已生成最小 backend/.env"
    fi
  fi
}

ensure_python_deps() {
  if ! "$PYTHON_BIN" -c "import fastapi,uvicorn,sqlalchemy,alembic" >/dev/null 2>&1; then
    echo "📦 检测到缺少 Python 依赖，尝试执行用户态安装..."
    "$PYTHON_BIN" -m pip install --user --break-system-packages -r "$BACKEND_DIR/requirements.txt"
  fi
}

run_migrations() {
  cd "$BACKEND_DIR"
  export PATH="$HOME/.local/bin:$PATH"
  ~/.local/bin/alembic upgrade head
}

start_local_processes() {
  stop_local_processes
  ensure_backend_env
  ensure_python_deps
  run_migrations

  nohup bash -lc "cd '$BACKEND_DIR' && export PATH=\"$HOME/.local/bin:$PATH\" && uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}" > "$LOG_DIR/backend.log" 2>&1 &
  nohup bash -lc "cd '$MOBILE_DIR' && python3 -m http.server ${MOBILE_PORT}" > "$LOG_DIR/frontend-mobile.log" 2>&1 &
  nohup bash -lc "cd '$ADMIN_DIR' && python3 -m http.server ${ADMIN_PORT}" > "$LOG_DIR/frontend-admin.log" 2>&1 &

  sleep 2
  echo "📋 Local dev process status:"
  ss -lntp | grep -E ":(${BACKEND_PORT}|${MOBILE_PORT}|${ADMIN_PORT})\\b" || true
  echo
  curl -fsS "http://127.0.0.1:${BACKEND_PORT}/healthz" || true
}

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  cd "$DEPLOY_DIR"
  docker compose up -d --build
  print_access_urls
  echo "📋 Container status:"
  docker compose ps
else
  echo "ℹ️ docker compose 不可用，自动切换到本地开发模式（uvicorn + http.server）。"
  start_local_processes
  print_access_urls
fi
