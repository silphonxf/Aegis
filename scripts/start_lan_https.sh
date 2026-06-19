#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
MOBILE_DIR="$ROOT_DIR/frontend-mobile"
ADMIN_DIR="$ROOT_DIR/frontend-admin"
LOG_DIR="$ROOT_DIR/.logs"
CERT_DIR="$ROOT_DIR/.certs"
CERT_FILE="$CERT_DIR/dev-lan.crt"
KEY_FILE="$CERT_DIR/dev-lan.key"

mkdir -p "$LOG_DIR" "$CERT_DIR"

LAN_IP="$(hostname -I | awk '{print $1}')"
if [[ -z "$LAN_IP" ]]; then
  LAN_IP="127.0.0.1"
fi

stop_all() {
  fuser -k 8000/tcp 2>/dev/null || true
  fuser -k 5173/tcp 2>/dev/null || true
  fuser -k 5174/tcp 2>/dev/null || true
  pkill -f "scripts/serve_https.py --host 0.0.0.0 --port 5173" || true
  pkill -f "scripts/serve_https.py --host 0.0.0.0 --port 5174" || true
}

gen_cert() {
  local ips san_args
  ips="$(hostname -I 2>/dev/null | awk '{for(i=1;i<=NF;i++) print $i}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | sort -u || true)"
  san_args="subjectAltName=IP:127.0.0.1,DNS:localhost"
  while IFS= read -r ip; do
    [[ -z "$ip" || "$ip" == "127.0.0.1" ]] && continue
    san_args="${san_args},IP:${ip}"
  done <<< "$ips"

  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$KEY_FILE" -out "$CERT_FILE" \
    -subj "/CN=$LAN_IP" \
    -addext "$san_args"
}

start_services() {
  stop_all
  gen_cert

  nohup bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && export DATABASE_URL='sqlite:///./aegis.db' && uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-certfile '$CERT_FILE' --ssl-keyfile '$KEY_FILE'" > "$LOG_DIR/backend-https.log" 2>&1 &

  nohup python3 "$ROOT_DIR/scripts/serve_https.py" --host 0.0.0.0 --port 5173 --dir "$MOBILE_DIR" --cert "$CERT_FILE" --key "$KEY_FILE" > "$LOG_DIR/frontend-mobile-https.log" 2>&1 &

  nohup python3 "$ROOT_DIR/scripts/serve_https.py" --host 0.0.0.0 --port 5174 --dir "$ADMIN_DIR" --cert "$CERT_FILE" --key "$KEY_FILE" > "$LOG_DIR/frontend-admin-https.log" 2>&1 &

  sleep 1
}

start_services

echo "✅ Aegis HTTPS (LAN) started"
echo "- Mobile:  https://$LAN_IP:5173"
echo "- Admin:   https://$LAN_IP:5174"
echo "- API:     https://$LAN_IP:8000"
echo
echo "⚠️ 首次访问需在手机/浏览器信任自签名证书，否则相机/NFC等能力可能仍被拦截。"
echo "📄 logs:"
echo "- $LOG_DIR/backend-https.log"
echo "- $LOG_DIR/frontend-mobile-https.log"
echo "- $LOG_DIR/frontend-admin-https.log"
