# Aegis 对接 OpenClaw 的 AI Provider 技术设计（第一版）

> 更新时间：2026-05-07  
> 目标：先把 Aegis 的 AI 能力从“写死本地实现”改造成“可切换 provider”的结构，为后续接 OpenClaw 做准备。

---

## 1. 设计目标

当前 Aegis 的 AI 能力主要包括：

- `/api/v1/ai/diagnose`
- `/api/v1/ai/chat`
- `/api/v1/ai/offline/analyze`

现状问题：

1. 后端 AI 逻辑主要耦合在 `api/ai.py`
2. 默认实现偏向本地 Ollama + fallback 规则引擎
3. 后续若接入 OpenClaw，会导致 API 层继续膨胀
4. 前端无法感知当前使用的是哪种 AI provider

第一版设计目标：

- 先完成 provider 抽象
- 保持现有接口不破坏
- 为后续 `openclaw` provider 留出稳定接入点
- 继续保留本地 `ollama / fallback rules` 能力作为降级方案

---

## 2. provider 抽象原则

统一抽象三类能力：

1. **诊断类**：`diagnose`
2. **聊天类**：`chat`
3. **日志分析类**：`offline_analyze`

对外由 API 层调用统一 service：

- `backend/app/services/ai_provider.py`

provider 第一版支持：

- `mock`（规则建议 / 本地 fallback）
- `ollama`（本地离线模型）
- `openclaw`（先落接口骨架，后续再完成真正远端接入）

---

## 3. 配置设计

新增配置：

```env
AI_PROVIDER=ollama
AI_FALLBACK_PROVIDER=mock
OPENCLAW_BASE_URL=
OPENCLAW_API_KEY=
OPENCLAW_TIMEOUT_SECONDS=120
OPENCLAW_CHAT_PATH=/aegis/ai/chat
OPENCLAW_DIAGNOSE_PATH=/aegis/ai/diagnose
OPENCLAW_LOG_ANALYZE_PATH=/aegis/ai/log-analyze
```

说明：

- `AI_PROVIDER`：主 provider，后续可切换为 `openclaw`
- `AI_FALLBACK_PROVIDER`：主 provider 不可用时的回退 provider
- `OPENCLAW_*`：后续接 OpenClaw 网关时使用

---

## 4. 第一版架构

### 4.1 API 层职责

`api/ai.py` 只负责：

- 参数接收
- 调用 provider service
- 持久化诊断结果 / 日志分析结果
- 审计记录
- 返回统一响应

### 4.2 Service 层职责

`ai_provider.py` 负责：

- 根据配置选择 provider
- 调用对应实现
- 失败时执行 fallback
- 返回统一结构

### 4.3 OpenClaw Client 职责

`openclaw_client.py` 负责：

- 构造 HTTP 请求
- 统一鉴权头
- 统一处理超时/网络错误/非 JSON 返回

第一版先落 client 骨架，不要求马上具备完整远程可调能力。

---

## 5. 统一返回结构

### diagnose

```json
{
  "mode": "offline_ollama|openclaw|rule_fallback",
  "severity": "low|medium|high",
  "summary": "一句话结论",
  "suggestions": ["..."],
  "elapsed_ms": 123,
  "fallback_reason": null
}
```

### chat

```json
{
  "conversation_id": "chat-1",
  "mode": "offline_ollama|openclaw|rule_fallback",
  "summary": "摘要",
  "reply": "对话回复",
  "severity": "medium",
  "suggestions": ["..."],
  "attachment_notes": ["..."],
  "elapsed_ms": 123,
  "fallback_reason": null
}
```

### offline_analyze

```json
{
  "mode": "offline_ollama|openclaw|rule_fallback",
  "severity": "medium",
  "summary": "摘要",
  "matched_rules": [],
  "suggestions": [],
  "excerpt": "...",
  "elapsed_ms": 123,
  "fallback_reason": null
}
```

---

## 6. OpenClaw provider 后续接入思路

后续如果要让异地 Aegis 调你本机 OpenClaw，建议保持 Aegis 不感知底层实现，只感知 provider：

- Aegis -> `openclaw_client.py`
- `openclaw_client.py` -> OpenClaw 兼容入口
- OpenClaw 返回统一 JSON

这样后续无论 OpenClaw 是：

- HTTP webhook 入口
- Gateway 路由入口
- 异步任务桥接入口

Aegis 侧都不用大改。

---

## 7. 第一版落地范围

本次只做：

- provider 抽象
- 配置项补齐
- OpenClaw client 骨架
- diagnose/chat/offline_analyze 走 provider service
- 文档补充

本次**不做**：

- 真正打通 OpenClaw 远程网关
- 多模态大文件上传优化
- streaming 回复
- provider 可视化状态页

---

## 8. OpenClaw 远程接入第二阶段设计

### 8.1 目标

让部署在异地的 Aegis 也能调用你本机 OpenClaw，同时不依赖：

- 公网 IP
- 额外内网穿透工具

可行前提是：OpenClaw 当前已有可被外部触达或可由中心网关转发的入口能力（类似现有消息平台接入方式）。

### 8.2 推荐接入顺序

#### 路线 A（首选）：同步 HTTP 风格入口

目标形态：

- Aegis -> OpenClaw Gateway 兼容 HTTP 入口
- OpenClaw 返回同步 JSON

建议入口：

- `POST /aegis/ai/chat`
- `POST /aegis/ai/diagnose`
- `POST /aegis/ai/log-analyze`

建议鉴权：

- `Authorization: Bearer <OPENCLAW_API_KEY>`
- 或增加 `X-Aegis-Instance` / `X-Aegis-Signature` 作为扩展字段

#### 路线 B（备选）：异步任务桥接

适用于 OpenClaw 无法稳定提供同步 HTTP JSON 返回时：

- Aegis 发送任务到 OpenClaw 可达入口
- OpenClaw 异步处理
- 结果通过回调 URL / 中间存储 / 轮询读取返回 Aegis

该路线适合：

- AI 日志分析
- 批量错误日志研判

但不适合高实时聊天。

### 8.3 建议协议

#### Aegis -> OpenClaw：chat

```json
{
  "type": "chat",
  "conversation_id": "mobile-ai-chat",
  "message": "帮我分析这段错误日志",
  "attachments": [
    {
      "name": "error.log",
      "type": "text/plain",
      "size": 10240,
      "data_url": "data:text/plain;base64,xxxx"
    }
  ],
  "context": {
    "source": "aegis-mobile",
    "module": "ai_qa",
    "user": "admin"
  }
}
```

#### OpenClaw -> Aegis：chat

```json
{
  "ok": true,
  "mode": "openclaw",
  "conversation_id": "mobile-ai-chat",
  "summary": "数据库连接波动",
  "reply": "我看了一下，更像是数据库连接池或下游抖动导致的超时。",
  "severity": "medium",
  "suggestions": [
    "先检查连接池当前占用",
    "检查数据库和应用之间的网络抖动"
  ],
  "attachment_notes": [
    "已接收附件：error.log"
  ],
  "elapsed_ms": 820
}
```

#### Aegis -> OpenClaw：diagnose / log-analyze

```json
{
  "type": "log_analyze",
  "title": "错误日志分析",
  "detail": "...",
  "severity": "medium",
  "context": {
    "source": "aegis-selfcheck",
    "module": "offline_analyze"
  }
}
```

#### OpenClaw -> Aegis：diagnose / log-analyze

```json
{
  "ok": true,
  "mode": "openclaw",
  "summary": "命中数据库连接异常与请求超时特征",
  "severity": "high",
  "matched_rules": [
    {"code": "DB_CONN_FAIL", "severity": "high"}
  ],
  "suggestions": [
    "检查数据库可用性",
    "检查连接池配置"
  ],
  "excerpt": "...",
  "elapsed_ms": 950
}
```

### 8.4 Aegis 侧下一步实现建议

1. 让 `openclaw_client.py` 支持：
   - chat / diagnose / log-analyze 三种请求构造
   - 统一鉴权头
   - 更细粒度超时与错误码

2. 给 provider 增加：
   - `provider=openclaw` 下的字段校验
   - 对 OpenClaw 返回结果的 schema 校验
   - 降级到 `AI_FALLBACK_PROVIDER`

3. 前端后续补充：
   - 当前 AI provider 展示
   - provider 失败提示
   - 请求耗时展示

### 8.5 风险点

1. OpenClaw 当前未必天然提供同步 API 入口
2. 若只能走消息型入口，则聊天体验会退化为异步
3. 附件传输体积需要控制，建议：
   - 文本附件 <= 200KB
   - 图片 <= 2MB
   - 单次附件 <= 5 个
4. 必须做好鉴权、审计、来源限制

## 9. 下一步建议

在第一版 provider 抽象完成后，下一轮建议按这个顺序推进：

1. 验证 OpenClaw Gateway 是否支持同步 HTTP 风格接入
2. 明确 OpenClaw 请求/响应协议
3. 实现 `openclaw` provider 真正远程调用
4. 在前端增加 AI provider 状态显示
