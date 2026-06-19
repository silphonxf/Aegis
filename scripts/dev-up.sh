#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/code/backend"
MOBILE_DIR="$ROOT_DIR/code/frontend-mobile"
ADMIN_DIR="$ROOT_DIR/code/frontend-admin"
LOG_DIR="$ROOT_DIR/.logs"
CERT_DIR="$ROOT_DIR/.certs"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
mkdir -p "$LOG_DIR"

BACKEND_PORT="${AEGIS_BACKEND_PORT:-8000}"
MOBILE_PORT="${AEGIS_MOBILE_PORT:-5173}"
ADMIN_PORT="${AEGIS_ADMIN_PORT:-5174}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
HTTPS_CERT="${AEGIS_HTTPS_CERT:-$CERT_DIR/dev-lan.crt}"
HTTPS_KEY="${AEGIS_HTTPS_KEY:-$CERT_DIR/dev-lan.key}"
LOCAL_ADMIN_PASSWORD="${AEGIS_INIT_ADMIN_PASSWORD:-local_admin_pass_2026}"

VENV_PYTHON="${VENV_PYTHON:-$VENV_DIR/bin/python}"
VENV_UVICORN="${VENV_UVICORN:-$VENV_DIR/bin/uvicorn}"
VENV_ALEMBIC="${VENV_ALEMBIC:-$VENV_DIR/bin/alembic}"

get_lan_ips() {
  hostname -I 2>/dev/null | awk '{for(i=1;i<=NF;i++) print $i}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || true
}

print_access_urls() {
  local ips
  ips="$(get_lan_ips)"

  echo
  echo "🚀 Aegis services are up. Access URLs:"
  echo "- Backend API:     https://127.0.0.1:${BACKEND_PORT}"
  echo "- Admin Frontend:  https://127.0.0.1:${ADMIN_PORT}"
  echo "- Mobile Frontend: https://127.0.0.1:${MOBILE_PORT}"

  if [[ -n "$ips" ]]; then
    while IFS= read -r ip; do
      [[ -z "$ip" ]] && continue
      echo "- Backend API (LAN):     https://$ip:${BACKEND_PORT}"
      echo "- Admin Frontend (LAN):  https://$ip:${ADMIN_PORT}"
      echo "- Mobile Frontend (LAN): https://$ip:${MOBILE_PORT}"
    done <<< "$ips"
  fi

  echo
  echo "🔐 默认本地管理员: admin / ${LOCAL_ADMIN_PASSWORD}"
  echo "💡 前端 API 默认使用 https://当前页面主机:${BACKEND_PORT}"
  echo "📄 日志目录: $LOG_DIR"
  echo
}

stop_local_processes() {
  pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}" || true
  pkill -f "uvicorn app.main:app --reload --host 0.0.0.0 --port ${BACKEND_PORT}" || true
  pkill -f "python3 -m http.server ${MOBILE_PORT}" || true
  pkill -f "python3 -m http.server ${ADMIN_PORT}" || true
  pkill -f "serve_https.py --host 0.0.0.0 --port ${MOBILE_PORT}" || true
  pkill -f "serve_https.py --host 0.0.0.0 --port ${ADMIN_PORT}" || true
}

ensure_backend_env() {
  cd "$BACKEND_DIR"
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      cp .env.example .env
      "$VENV_PYTHON" - <<PY
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
  if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "❌ 未找到项目虚拟环境 Python: $VENV_PYTHON"
    exit 1
  fi
  if [[ ! -x "$VENV_UVICORN" || ! -x "$VENV_ALEMBIC" ]]; then
    echo "❌ 项目虚拟环境缺少 uvicorn 或 alembic，请先安装依赖。"
    exit 1
  fi
  if ! "$VENV_PYTHON" -c "import fastapi,uvicorn,sqlalchemy,alembic" >/dev/null 2>&1; then
    echo "❌ 项目虚拟环境依赖不完整，请先修复 .venv 后再启动。"
    exit 1
  fi
}

ensure_https_assets() {
  mkdir -p "$(dirname "$HTTPS_CERT")" "$(dirname "$HTTPS_KEY")"
  local ips san_args primary_cn
  ips="$(get_lan_ips | sort -u)"
  primary_cn="$(printf '%s\n' "$ips" | head -n 1)"
  [[ -n "$primary_cn" ]] || primary_cn="127.0.0.1"
  san_args="subjectAltName=IP:127.0.0.1,DNS:localhost"
  while IFS= read -r ip; do
    [[ -z "$ip" || "$ip" == "127.0.0.1" ]] && continue
    san_args="${san_args},IP:${ip}"
  done <<< "$ips"

  if [[ ! -f "$HTTPS_CERT" || ! -f "$HTTPS_KEY" ]] || ! openssl x509 -in "$HTTPS_CERT" -noout -ext subjectAltName 2>/dev/null | grep -Fq "$primary_cn"; then
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
      -keyout "$HTTPS_KEY" -out "$HTTPS_CERT" \
      -subj "/CN=${primary_cn}" \
      -addext "$san_args" >/dev/null 2>&1
    echo "ℹ️ 已生成/更新 HTTPS 自签名证书: $HTTPS_CERT"
  fi
}

run_migrations() {
  cd "$BACKEND_DIR"
  PYTHONPATH=. "$VENV_ALEMBIC" upgrade head
}

start_local_processes() {
  stop_local_processes
  ensure_backend_env
  ensure_python_deps
  ensure_https_assets
  run_migrations

  setsid -f bash -lc "cd '$BACKEND_DIR' && PYTHONPATH=. '$VENV_UVICORN' app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} --ssl-certfile '$HTTPS_CERT' --ssl-keyfile '$HTTPS_KEY' > '$LOG_DIR/backend-https.log' 2>&1"
  setsid -f bash -lc "'$VENV_PYTHON' '$ROOT_DIR/scripts/serve_https.py' --host 0.0.0.0 --port ${MOBILE_PORT} --dir '$MOBILE_DIR' --cert '$HTTPS_CERT' --key '$HTTPS_KEY' > '$LOG_DIR/frontend-mobile.log' 2>&1"
  setsid -f bash -lc "'$VENV_PYTHON' '$ROOT_DIR/scripts/serve_https.py' --host 0.0.0.0 --port ${ADMIN_PORT} --dir '$ADMIN_DIR' --cert '$HTTPS_CERT' --key '$HTTPS_KEY' > '$LOG_DIR/frontend-admin.log' 2>&1"

  sleep 3
  echo "📋 Local dev process status:"
  ss -lntp | grep -E ":(${BACKEND_PORT}|${MOBILE_PORT}|${ADMIN_PORT})\\b" || true
  echo
  curl -k -fsS "https://127.0.0.1:${BACKEND_PORT}/healthz" || true
  echo
  curl -k -I -fsS "https://127.0.0.1:${MOBILE_PORT}" | head -n 1 || true
  curl -k -I -fsS "https://127.0.0.1:${ADMIN_PORT}" | head -n 1 || true
}

echo "ℹ️ 使用 Codex 整理版本地开发模式（uvicorn + HTTPS static server）。"
start_local_processes
print_access_urls
