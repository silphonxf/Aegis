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

echo "[1/10] healthz"
curl -sS "$BASE/healthz" | python3 -m json.tool > /tmp/aegis_health.json

echo "[2/10] login"
LOGIN_RESP=$(curl -sS -X POST "$BASE/api/v1/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}")
TOKEN=$(printf '%s' "$LOGIN_RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token", ""))')

if [[ -z "$TOKEN" ]]; then
  echo "❌ 登录失败，未获取到 access_token。响应如下："
  echo "$LOGIN_RESP"
  exit 1
fi

AUTH="Authorization: Bearer $TOKEN"

echo "[3/10] me"
curl -sS "$BASE/api/v1/auth/me" -H "$AUTH" | python3 -m json.tool > /tmp/aegis_me.json

echo "[4/10] create system"
SYS_SUFFIX=$(date +%s)
SYSTEM_CODE="SMOKE-SYS-$SYS_SUFFIX"
SYSTEM_ID=$(curl -sS -X POST "$BASE/api/v1/admin/systems" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"system_code\":\"$SYSTEM_CODE\",\"name\":\"Smoke系统\",\"env\":\"test\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

echo "[5/10] create selfcheck template"
TEMPLATE_ID=$(curl -sS -X POST "$BASE/api/v1/selfchecks/templates" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"system_id\":$SYSTEM_ID,\"check_type\":\"daily\",\"name\":\"Smoke模板\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

echo "[6/10] create simple selfcheck"
curl -sS -X POST "$BASE/api/v1/selfchecks/records/simple" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"system_id\":$SYSTEM_ID,\"content\":\"Smoke自检\",\"result\":\"normal\",\"note\":\"from smoke\"}" | python3 -m json.tool > /tmp/aegis_selfcheck.json

echo "[7/10] create restart task + approve"
TASK_ID=$(curl -sS -X POST "$BASE/api/v1/toolbox/restart-task" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"target":"local-host","reason":"smoke"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
curl -sS -X PUT "$BASE/api/v1/toolbox/tasks/$TASK_ID/status" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"status":"approved","note":"smoke-pass"}' | python3 -m json.tool > /tmp/aegis_task_approved.json

echo "[8/10] ai diagnose"
curl -sS -X POST "$BASE/api/v1/ai/diagnose" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"title":"smoke","detail":"cpu load and timeout","severity":"medium"}' | python3 -m json.tool > /tmp/aegis_ai.json

echo "[9/10] create asset + summary"
ASSET_CODE="SMOKE-ASSET-$SYS_SUFFIX"
curl -sS -X POST "$BASE/api/v1/admin/assets" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"asset_code\":\"$ASSET_CODE\",\"name\":\"Smoke资产\",\"category\":\"server\",\"system_id\":$SYSTEM_ID,\"status\":\"in_use\"}" | python3 -m json.tool > /tmp/aegis_asset.json
curl -sS "$BASE/api/v1/admin/assets/summary" -H "$AUTH" | python3 -m json.tool > /tmp/aegis_asset_summary.json

echo "[10/10] audit logs"
curl -sS "$BASE/api/v1/admin/audit-logs?page=1&size=5" -H "$AUTH" | python3 -m json.tool > /tmp/aegis_audit.json

echo "OK: iteration3 smoke passed"
echo "artifacts: /tmp/aegis_health.json /tmp/aegis_me.json /tmp/aegis_selfcheck.json /tmp/aegis_task_approved.json /tmp/aegis_ai.json /tmp/aegis_asset.json /tmp/aegis_asset_summary.json /tmp/aegis_audit.json"
