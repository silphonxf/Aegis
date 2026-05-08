# Aegis 本地 OpenClaw AI Adapter 联调说明（第一版）

> 更新时间：2026-05-08 00:00+08:00

## 当前目标

先做出一个**本地可联调版本**，验证链路：

- Aegis `/api/v1/ai/chat`
- Aegis `/api/v1/ai/diagnose`
- Aegis `/api/v1/ai/offline/analyze`
- `openclaw_client.py`
- 本地 `OpenClaw AI Adapter` 骨架入口

## 当前实现

本地 adapter 入口已挂载在 Aegis 后端自身：

- `GET /aegis/ai/healthz`
- `POST /aegis/ai/chat`
- `POST /aegis/ai/diagnose`
- `POST /aegis/ai/log-analyze`

当前用途：

- 作为后续独立 OpenClaw AI Adapter 服务的本地联调骨架
- 先验证 `AI_PROVIDER=openclaw` 的端到端链路是通的

## 当前配置（本地联调）

`backend/.env` 已切到：

```env
AI_PROVIDER=openclaw
OPENCLAW_BASE_URL=http://127.0.0.1:8000
OPENCLAW_API_KEY=local-dev-openclaw-token
OPENCLAW_ADAPTER_ENABLED=true
OPENCLAW_ADAPTER_TOKEN=local-dev-openclaw-token
```

说明：

- 这不是最终公网部署形态
- 只是为了本地先把 provider -> adapter 的链路打通

## 已验证结果

### 1. 聊天接口

Aegis 调用：
- `POST /api/v1/ai/chat`

返回：
- `mode=openclaw`
- 能拿到 adapter 返回的 `summary/reply/suggestions`

### 2. 诊断接口

Aegis 调用：
- `POST /api/v1/ai/diagnose`

返回：
- `mode=openclaw`
- 能拿到 adapter 返回的诊断结果

### 3. Adapter 健康检查

- `GET /aegis/ai/healthz`
- 返回 `status=ok`

## 当前边界

本地 adapter 仍然是**骨架模式**：

- 还没有真的调用 OpenClaw agent / Gateway 执行 AI 能力
- 当前回复是由本地 mock / rule fallback 逻辑生成
- 但整个 provider 路径已经被验证打通

## 下一步建议

下一轮开发应拆成两个方向：

1. 将 adapter 从 Aegis 后端内嵌骨架，升级为独立服务或独立可部署模块
2. 让 adapter 真正调用本机 OpenClaw，而不是返回 mock/rule fallback 结果

## 备注

启动时仍需通过项目 `.venv` site-packages 优先级解决当前机器上的 Pydantic 2 / 项目 Pydantic 1 冲突问题。
