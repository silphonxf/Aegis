#!/usr/bin/env bash
set -euo pipefail

# 用法：
#   ./scripts/setup_offline_ai.sh                # 默认 qwen2.5:7b
#   ./scripts/setup_offline_ai.sh qwen2.5:14b    # 指定模型

MODEL="${1:-qwen2.5:7b}"
# 默认使用 /data 下当前用户可写目录，满足“模型放在 /data”要求且无需 root
DATA_DIR="/data/cache/ollama"
MODELS_DIR="$DATA_DIR/models"
LOG_DIR="$DATA_DIR/logs"

mkdir -p "$MODELS_DIR" "$LOG_DIR"

echo "[1/4] 检查 ollama"
if ! command -v ollama >/dev/null 2>&1; then
  echo "❌ 未检测到 ollama，请先安装 ollama"
  exit 1
fi

echo "[2/4] 启动 ollama（模型目录放 /data）"
# 若已有进程则先结束，避免环境变量不一致
pkill -f "ollama serve" >/dev/null 2>&1 || true

export OLLAMA_MODELS="$MODELS_DIR"
nohup ollama serve >"$LOG_DIR/ollama-serve.log" 2>&1 &

# 等待服务启动
for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "❌ ollama 启动失败，请检查 $LOG_DIR/ollama-serve.log"
  exit 1
fi

echo "[3/4] 拉取模型: $MODEL"
ollama pull "$MODEL"

echo "[4/4] 验证模型调用"
RESP=$(curl -fsS http://127.0.0.1:11434/api/generate -d "{\"model\":\"$MODEL\",\"prompt\":\"请用中文回复：离线模型已就绪\",\"stream\":false}")
echo "$RESP" | head -c 300

echo

echo "✅ 离线模型已就绪"
echo "   模型目录: $MODELS_DIR"
echo "   日志目录: $LOG_DIR"
echo "   Aegis 建议 .env 配置："
echo "OFFLINE_AI_ENABLED=true"
echo "OFFLINE_AI_PROVIDER=ollama"
echo "OFFLINE_AI_MODEL=$MODEL"
echo "OFFLINE_AI_OLLAMA_BASE_URL=http://127.0.0.1:11434"
