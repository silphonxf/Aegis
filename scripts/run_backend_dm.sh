#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/xf/.openclaw/workspace/code/aegis"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"
source .venv/bin/activate

export LD_LIBRARY_PATH="/data/DMdata/dmdbms/drivers/dpi:/data/DMdata/dmdbms/drivers/dpi/dependencies:${LD_LIBRARY_PATH:-}"

# 默认端口 8000，可通过第一个参数覆盖
PORT="${1:-8000}"
# 默认监听全部网卡，便于局域网移动端访问
HOST="${2:-0.0.0.0}"

exec uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
