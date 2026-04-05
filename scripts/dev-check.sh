#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
USER="${2:-admin}"
PASS="${3:-}"

if [[ -z "$PASS" ]]; then
  echo "❌ 缺少登录密码：请通过第3个参数提供。"
  echo "   示例: ./scripts/dev-check.sh http://127.0.0.1:8000 admin your-password"
  exit 1
fi

echo "[1/3] healthz"
curl -fsS "$BASE/healthz" | python3 -m json.tool >/tmp/aegis_devcheck_health.json

echo "[2/3] login"
LOGIN_RESP=$(curl -fsS -X POST "$BASE/api/v1/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}")
TOKEN=$(python3 - <<'PY'
import json,sys
print(json.loads(sys.stdin.read()).get('access_token',''))
PY
<<< "$LOGIN_RESP")

if [[ -z "$TOKEN" ]]; then
  echo "❌ 登录失败"
  exit 1
fi
AUTH="Authorization: Bearer $TOKEN"

echo "[3/3] me"
curl -fsS "$BASE/api/v1/auth/me" -H "$AUTH" | python3 -m json.tool >/tmp/aegis_devcheck_me.json

echo "OK: basic dev check passed"
echo "artifacts: /tmp/aegis_devcheck_health.json /tmp/aegis_devcheck_me.json"
