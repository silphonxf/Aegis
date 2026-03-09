#!/usr/bin/env bash
set -euo pipefail
trap 'report_fail "command_failed"' ERR

ROOT_DIR="/home/xf/.openclaw/workspace/code/aegis"
BACKEND_DIR="$ROOT_DIR/backend"
PORT="${1:-8001}"
REPORT_PATH="${2:-/tmp/aegis_dm_check_report.json}"
CURRENT_STEP="init"

report_fail() {
  local reason="$1"
  python - <<'PY' "$REPORT_PATH" "$CURRENT_STEP" "$reason"
import json,sys,datetime
path,step,reason=sys.argv[1],sys.argv[2],sys.argv[3]
payload={
  "ok": False,
  "failed_step": step,
  "reason": reason,
  "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
with open(path,"w",encoding="utf-8") as f:
  json.dump(payload,f,ensure_ascii=False,indent=2)
print(f"🧾 已写入失败报告: {path}")
PY
}

cd "$BACKEND_DIR"

if [[ ! -f .env ]]; then
  echo "❌ 未找到 $BACKEND_DIR/.env，请先配置数据库连接"
  CURRENT_STEP="precheck_env"
  report_fail "env_missing"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "❌ 未找到 Python 虚拟环境 .venv，请先执行依赖安装"
  CURRENT_STEP="precheck_venv"
  report_fail "venv_missing"
  exit 1
fi

source .venv/bin/activate

export LD_LIBRARY_PATH="/data/DMdata/dmdbms/drivers/dpi:/data/DMdata/dmdbms/drivers/dpi/dependencies:${LD_LIBRARY_PATH:-}"

CURRENT_STEP="dm_port"
echo "== [1/6] 检查达梦端口 127.0.0.1:5236 =="
python - <<'PY'
import socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect(("127.0.0.1", 5236))
    print("✅ 达梦端口可达")
except Exception as e:
    print(f"❌ 达梦端口不可达: {e}")
    sys.exit(1)
finally:
    s.close()
PY

CURRENT_STEP="alembic_upgrade"
echo "== [2/6] 执行 Alembic 迁移 =="
alembic upgrade head
echo "✅ Alembic 迁移完成"

CURRENT_STEP="start_backend"
echo "== [3/6] 启动后端服务 (port: ${PORT}) =="
uvicorn app.main:app --host 127.0.0.1 --port "$PORT" > /tmp/aegis_dm_check.log 2>&1 &
SERVER_PID=$!
cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# 等待服务就绪（最多 20 秒）
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

CURRENT_STEP="healthz"
echo "== [4/6] 健康检查 =="
health_resp=$(curl -fsS "http://127.0.0.1:${PORT}/healthz")
echo "$health_resp"
if [[ "$health_resp" != *'"status":"ok"'* ]]; then
  echo "❌ /healthz 返回异常"
  exit 1
fi
echo "✅ /healthz 正常"

CURRENT_STEP="auth_login"
echo "== [5/6] 登录检查 =="
login_resp=$(curl -fsS -X POST "http://127.0.0.1:${PORT}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}')

echo "$login_resp"
if [[ "$login_resp" != *'"access_token"'* ]]; then
  echo "❌ 登录失败：未返回 access_token"
  exit 1
fi

echo "✅ 登录正常（已返回 access_token）"

token=$(python - <<'PY'
import json,sys
print(json.loads(sys.stdin.read()).get("access_token", ""))
PY
<<< "$login_resp")

if [[ -z "$token" ]]; then
  echo "❌ 登录响应解析失败：access_token 为空"
  exit 1
fi

CURRENT_STEP="write_paths"
echo "== [6/6] 写库接口检查（profile + change-password） =="
new_nickname="dm-check-$(date +%s)"

profile_resp=$(curl -fsS -X PUT "http://127.0.0.1:${PORT}/api/v1/auth/profile" \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -d "{\"nickname\":\"${new_nickname}\",\"avatar_url\":null}")

echo "$profile_resp"
if [[ "$profile_resp" != *"\"nickname\":\"${new_nickname}\""* ]]; then
  echo "❌ profile 写库失败：nickname 未更新"
  exit 1
fi

echo "✅ profile 写库正常"

change_pwd_resp=$(curl -fsS -X POST "http://127.0.0.1:${PORT}/api/v1/auth/change-password" \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -d '{"old_password":"admin123","new_password":"admin123_tmp"}')

echo "$change_pwd_resp"
if [[ "$change_pwd_resp" != *'"ok":true'* ]]; then
  echo "❌ change-password 写库失败（admin123 -> admin123_tmp）"
  exit 1
fi

echo "✅ change-password 写库正常（admin123 -> admin123_tmp）"

# 将密码改回默认值，避免影响后续检查
relogin_resp=$(curl -fsS -X POST "http://127.0.0.1:${PORT}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123_tmp"}')

tmp_token=$(python - <<'PY'
import json,sys
print(json.loads(sys.stdin.read()).get("access_token", ""))
PY
<<< "$relogin_resp")

if [[ -z "$tmp_token" ]]; then
  echo "❌ 临时密码回登失败，无法执行密码回滚，请手动检查"
  exit 1
fi

rollback_resp=$(curl -fsS -X POST "http://127.0.0.1:${PORT}/api/v1/auth/change-password" \
  -H "Authorization: Bearer $tmp_token" \
  -H 'Content-Type: application/json' \
  -d '{"old_password":"admin123_tmp","new_password":"admin123"}')

echo "$rollback_resp"
if [[ "$rollback_resp" != *'"ok":true'* ]]; then
  echo "❌ 密码回滚失败（admin123_tmp -> admin123），请手动恢复"
  exit 1
fi

echo "✅ 密码已回滚为 admin123"

CURRENT_STEP="done"
python - <<'PY' "$REPORT_PATH" "$PORT"
import json,sys,datetime
path,port=sys.argv[1],sys.argv[2]
payload={
  "ok": True,
  "port": int(port),
  "checks": [
    "dm_port",
    "alembic_upgrade",
    "start_backend",
    "healthz",
    "auth_login",
    "write_paths",
  ],
  "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
with open(path,"w",encoding="utf-8") as f:
  json.dump(payload,f,ensure_ascii=False,indent=2)
print(f"🧾 已写入检查报告: {path}")
PY

echo "\n🎉 达梦接入检查通过（含关键写库接口）"
