#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-${SMOKE_BASE:-http://127.0.0.1:8000}}"
USER="${2:-${SMOKE_USER:-admin}}"
PASS="${3:-${SMOKE_PASS:-}}"

if [[ -z "$PASS" ]]; then
  echo "❌ 缺少登录密码：请通过第3个参数或环境变量 SMOKE_PASS 提供。"
  echo "   示例: ./scripts/iteration3_smoke.sh http://127.0.0.1:8000 admin 'your-password'"
  exit 1
fi

echo "[1/7] login"
LOGIN_RESP=$(curl -sS -X POST "$BASE/api/v1/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}")
TOKEN=$(python3 - <<'PY'
import json,sys
raw=sys.stdin.read().strip()
try:
    data=json.loads(raw)
except Exception:
    print("")
    sys.exit(0)
print(data.get("access_token", ""))
PY
<<< "$LOGIN_RESP")

if [[ -z "$TOKEN" ]]; then
  echo "❌ 登录失败，未获取到 access_token。响应如下："
  echo "$LOGIN_RESP"
  exit 1
fi

AUTH="Authorization: Bearer $TOKEN"

echo "[2/7] toolbox ping"
curl -sS -X POST "$BASE/api/v1/toolbox/ping" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"host":"127.0.0.1","count":1}' | python3 -m json.tool > /tmp/aegis_ping.json

echo "[3/7] toolbox port-check"
curl -sS -X POST "$BASE/api/v1/toolbox/port-check" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"host":"127.0.0.1","port":8000,"timeout_ms":1200}' | python3 -m json.tool > /tmp/aegis_port.json

echo "[4/7] create restart task"
TASK_ID=$(curl -sS -X POST "$BASE/api/v1/toolbox/restart-task" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"target":"local-host","reason":"smoke"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

echo "[5/7] approve task"
curl -sS -X PUT "$BASE/api/v1/toolbox/tasks/$TASK_ID/status" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"status":"approved","note":"smoke-pass"}' | python3 -m json.tool > /tmp/aegis_task_approved.json

echo "[6/7] ai diagnose"
curl -sS -X POST "$BASE/api/v1/ai/diagnose" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"smoke","detail":"cpu load and timeout","severity":"medium"}' | python3 -m json.tool > /tmp/aegis_ai.json

echo "[7/7] ai history"
curl -sS "$BASE/api/v1/ai/diagnoses?page=1&size=5" -H "$AUTH" | python3 -m json.tool > /tmp/aegis_ai_history.json

echo "OK: iteration3 smoke passed"
echo "artifacts: /tmp/aegis_ping.json /tmp/aegis_port.json /tmp/aegis_task_approved.json /tmp/aegis_ai.json /tmp/aegis_ai_history.json"
