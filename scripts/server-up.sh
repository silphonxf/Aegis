#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
MOBILE_DIR="$ROOT_DIR/frontend-mobile"
ADMIN_DIR="$ROOT_DIR/frontend-admin"
LOG_DIR="${AEGIS_LOG_DIR:-$ROOT_DIR/.logs}"
CERT_DIR="${AEGIS_CERT_DIR:-$ROOT_DIR/.certs}"
VENV_DIR="${AEGIS_VENV_DIR:-$ROOT_DIR/.venv}"

BACKEND_PORT="${AEGIS_BACKEND_PORT:-8000}"
MOBILE_PORT="${AEGIS_MOBILE_PORT:-5173}"
ADMIN_PORT="${AEGIS_ADMIN_PORT:-5174}"
HOST="${AEGIS_HOST:-0.0.0.0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PYTHON="${VENV_PYTHON:-$VENV_DIR/bin/python}"
VENV_UVICORN="${VENV_UVICORN:-$VENV_DIR/bin/uvicorn}"
VENV_ALEMBIC="${VENV_ALEMBIC:-$VENV_DIR/bin/alembic}"
HTTPS_CERT="${AEGIS_HTTPS_CERT:-$CERT_DIR/server.crt}"
HTTPS_KEY="${AEGIS_HTTPS_KEY:-$CERT_DIR/server.key}"

mkdir -p "$LOG_DIR" "$CERT_DIR"

get_lan_ips() {
  hostname -I 2>/dev/null | awk '{for(i=1;i<=NF;i++) print $i}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || true
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "Missing required file: $1"
    exit 1
  fi
}

ensure_venv() {
  if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Python virtualenv not found: $VENV_PYTHON"
    echo "Create it first:"
    echo "  cd '$ROOT_DIR'"
    echo "  $PYTHON_BIN -m venv .venv"
    echo "  .venv/bin/pip install -r backend/requirements.txt"
    exit 1
  fi
  if [[ ! -x "$VENV_UVICORN" || ! -x "$VENV_ALEMBIC" ]]; then
    echo "uvicorn or alembic is missing in virtualenv. Install dependencies:"
    echo "  cd '$ROOT_DIR'"
    echo "  .venv/bin/pip install -r backend/requirements.txt"
    exit 1
  fi
}

validate_backend_env() {
  require_file "$BACKEND_DIR/.env"

  if grep -Ev '^[[:space:]]*#' "$BACKEND_DIR/.env" | grep -Eq 'change_me|replace_with|your_server_ip_or_domain|admin123|local_admin_pass_2026|test_secret_key'; then
    echo "backend/.env still contains weak local defaults or placeholders."
    echo "Update SECRET_KEY and INIT_ADMIN_PASSWORD before starting on a server."
    exit 1
  fi

  cd "$BACKEND_DIR"
  PYTHONPATH=. "$VENV_PYTHON" - <<'PY'
from app.core.config import settings

db = settings.effective_database_url
print(f"APP_ENV={settings.APP_ENV}")
print(f"DATABASE={db.split('@')[-1] if '@' in db else db}")
print(f"AI_PROVIDER={settings.AI_PROVIDER}")
print(f"OFFLINE_AI_ENABLED={settings.OFFLINE_AI_ENABLED}")
PY
}

ensure_https_assets() {
  if [[ -f "$HTTPS_CERT" && -f "$HTTPS_KEY" ]]; then
    return
  fi

  local ips san_args primary_cn
  ips="$(get_lan_ips | sort -u)"
  primary_cn="$(printf '%s\n' "$ips" | head -n 1)"
  [[ -n "$primary_cn" ]] || primary_cn="127.0.0.1"
  san_args="subjectAltName=IP:127.0.0.1,DNS:localhost"
  while IFS= read -r ip; do
    [[ -z "$ip" || "$ip" == "127.0.0.1" ]] && continue
    san_args="${san_args},IP:${ip}"
  done <<< "$ips"

  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$HTTPS_KEY" -out "$HTTPS_CERT" \
    -subj "/CN=${primary_cn}" \
    -addext "$san_args" >/dev/null 2>&1
  echo "Generated self-signed HTTPS certificate: $HTTPS_CERT"
}

run_migrations() {
  cd "$BACKEND_DIR"
  PYTHONPATH=. "$VENV_ALEMBIC" upgrade head
}

stop_services() {
  pkill -f "uvicorn app.main:app --host ${HOST} --port ${BACKEND_PORT}" || true
  pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}" || true
  pkill -f "serve_https.py --host ${HOST} --port ${MOBILE_PORT}" || true
  pkill -f "serve_https.py --host ${HOST} --port ${ADMIN_PORT}" || true
  pkill -f "serve_https.py --host 0.0.0.0 --port ${MOBILE_PORT}" || true
  pkill -f "serve_https.py --host 0.0.0.0 --port ${ADMIN_PORT}" || true
}

start_services() {
  ensure_venv
  validate_backend_env
  ensure_https_assets
  run_migrations
  stop_services

  setsid -f bash -lc "cd '$BACKEND_DIR' && PYTHONPATH=. '$VENV_UVICORN' app.main:app --host '$HOST' --port '$BACKEND_PORT' --ssl-certfile '$HTTPS_CERT' --ssl-keyfile '$HTTPS_KEY' > '$LOG_DIR/backend-https.log' 2>&1"
  setsid -f bash -lc "'$VENV_PYTHON' '$ROOT_DIR/scripts/serve_https.py' --host '$HOST' --port '$MOBILE_PORT' --dir '$MOBILE_DIR' --cert '$HTTPS_CERT' --key '$HTTPS_KEY' > '$LOG_DIR/frontend-mobile.log' 2>&1"
  setsid -f bash -lc "'$VENV_PYTHON' '$ROOT_DIR/scripts/serve_https.py' --host '$HOST' --port '$ADMIN_PORT' --dir '$ADMIN_DIR' --cert '$HTTPS_CERT' --key '$HTTPS_KEY' > '$LOG_DIR/frontend-admin.log' 2>&1"

  sleep 3
  status_services
  print_urls
}

status_services() {
  echo "Port status:"
  ss -lntp | grep -E ":(${BACKEND_PORT}|${MOBILE_PORT}|${ADMIN_PORT})\\b" || echo "No Aegis ports are listening."

  echo
  echo "Backend health:"
  curl -k -fsS "https://127.0.0.1:${BACKEND_PORT}/healthz" || echo "backend healthz unavailable"
  echo
}

print_urls() {
  local ips
  ips="$(get_lan_ips)"

  echo "Access URLs:"
  echo "- Backend API:     https://127.0.0.1:${BACKEND_PORT}"
  echo "- Mobile Frontend: https://127.0.0.1:${MOBILE_PORT}"
  echo "- Admin Frontend:  https://127.0.0.1:${ADMIN_PORT}"
  while IFS= read -r ip; do
    [[ -z "$ip" ]] && continue
    echo "- Backend API:     https://${ip}:${BACKEND_PORT}"
    echo "- Mobile Frontend: https://${ip}:${MOBILE_PORT}"
    echo "- Admin Frontend:  https://${ip}:${ADMIN_PORT}"
  done <<< "$ips"
  echo "Logs: $LOG_DIR"
}

case "${1:-start}" in
  start)
    start_services
    ;;
  stop)
    stop_services
    echo "Aegis services stopped."
    ;;
  restart)
    stop_services
    start_services
    ;;
  status)
    status_services
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 2
    ;;
esac
