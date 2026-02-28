#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/xf/.openclaw/workspace/code/aegis"
BACKEND_DIR="$ROOT_DIR/backend"
PORT="${1:-8001}"

cd "$BACKEND_DIR"

if [[ ! -f .env ]]; then
  echo "❌ 未找到 $BACKEND_DIR/.env，请先配置数据库连接"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "❌ 未找到 Python 虚拟环境 .venv，请先执行依赖安装"
  exit 1
fi

source .venv/bin/activate

export LD_LIBRARY_PATH="/data/DMdata/dmdbms/drivers/dpi:/data/DMdata/dmdbms/drivers/dpi/dependencies:${LD_LIBRARY_PATH:-}"

echo "== [1/5] 检查达梦端口 127.0.0.1:5236 =="
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

echo "== [2/5] 执行 Alembic 迁移 =="
alembic upgrade head
echo "✅ Alembic 迁移完成"

echo "== [3/5] 启动后端服务 (port: ${PORT}) =="
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

echo "== [4/5] 健康检查 =="
health_resp=$(curl -fsS "http://127.0.0.1:${PORT}/healthz")
echo "$health_resp"
if [[ "$health_resp" != *'"status":"ok"'* ]]; then
  echo "❌ /healthz 返回异常"
  exit 1
fi
echo "✅ /healthz 正常"

echo "== [5/5] 登录检查 =="
login_resp=$(curl -fsS -X POST "http://127.0.0.1:${PORT}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}')

echo "$login_resp"
if [[ "$login_resp" != *'"access_token"'* ]]; then
  echo "❌ 登录失败：未返回 access_token"
  exit 1
fi

echo "✅ 登录正常（已返回 access_token）"
echo "\n🎉 达梦接入检查通过"
