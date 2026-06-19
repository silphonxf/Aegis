# Aegis 离线 AI 接入（Ollama + Qwen）

## 目标
将 Aegis 的 AI 诊断从 mock 升级为本地离线模型推理，模型文件存放在 `/data`（默认 `/data/cache/ollama/models`）。

## 推荐模型
- `qwen2.5:7b`（中文能力好，资源占用相对可控）
- 机器内存充足时可换 `qwen2.5:14b`

## 一键安装
```bash
cd /home/xf/.openclaw/workspace/code/aegis
./scripts/setup_offline_ai.sh
# 或指定模型
./scripts/setup_offline_ai.sh qwen2.5:14b
```

该脚本会：
1. 启动 Ollama
2. 将模型目录固定到 `/data/cache/ollama/models`（位于 /data 下）
3. 拉取 Qwen 模型
4. 做一次本地推理验证

## 后端配置（backend/.env）
```env
OFFLINE_AI_ENABLED=true
OFFLINE_AI_PROVIDER=ollama
OFFLINE_AI_MODEL=qwen2.5:7b
OFFLINE_AI_OLLAMA_BASE_URL=http://127.0.0.1:11434
OFFLINE_AI_TIMEOUT_SECONDS=120
```

## 功能行为
- `/api/v1/ai/diagnose`
  - 优先调用离线 LLM（mode=`offline_ollama`）
  - 若本地模型不可用自动回退规则建议（mode=`rule_fallback`）

- `/api/v1/ai/offline/analyze`
  - 优先离线 LLM输出 `severity/summary/suggestions/matched_rules`
  - 失败时回退内置规则引擎

## 验证
```bash
# 1) 健康检查
curl -s http://127.0.0.1:8000/healthz

# 2) 登录拿 token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 3) 诊断测试
curl -s -X POST http://127.0.0.1:8000/api/v1/ai/diagnose \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"DB timeout","detail":"service timeout and could not connect to db","severity":"medium"}' | python3 -m json.tool
```
