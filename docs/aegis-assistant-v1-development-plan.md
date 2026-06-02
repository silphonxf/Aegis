# Aegis Assistant V1 开发文档

## 1. 目标

将 Aegis 当前的 AI 问答升级为可执行系统能力的超级 AI 助手。V1 目标不是做通用 Agent，而是完成一个可扩展、可插拔、可控风险的 Assistant 基座，让用户可以通过自然语言直接查询、分析并触发 Aegis 内部能力。

V1 的核心目标：

- 提供统一助手入口接口
- 支持工具注册与调用
- 支持连续会话上下文
- 支持高风险操作确认流
- 支持首批查询 / 分析 / 审批工具
- 为后续新增更多功能保留稳定扩展点

---

## 2. 设计原则

### 2.1 工具化而不是写死逻辑

Assistant 不应堆砌在单一聊天接口中。所有可执行能力都应抽象为独立工具（tool），以便后续新增功能时只需新增工具实现与注册信息。

### 2.2 Router 与 Tool 解耦

Router 负责意图识别与工具选择；Tool 负责具体业务执行。不要在 Router 中嵌入业务细节。

### 2.3 后端主导权限与风险控制

是否允许执行、是否需要确认，必须由后端 policy 决定，不能依赖前端自行判断。

### 2.4 上下文由后端统一维护

前端只负责传递 `conversation_id`，上下文解析（如“它”“刚才那个系统”）由后端完成。

### 2.5 返回协议预留扩展能力

Assistant 返回结构中必须预留 actions / cards / tool_calls / pending_action / context 等字段，以便后续扩展多工具、多卡片、多步任务。

---

## 3. V1 范围

V1 先完成以下 4 类能力：

1. 查询系统状态
2. 查询巡检 / 自检记录
3. 分析日志文本
4. 发起重启审批（高风险确认）

V1 暂不追求：

- 通用多步自治 Agent
- 任意 SQL / 任意业务对象自发现
- 批量高风险自动执行
- 复杂工作流编排

---

## 4. 目录规划

### 4.1 后端服务目录

```text
backend/app/services/assistant/
  __init__.py
  router.py
  executor.py
  tool_registry.py
  context_manager.py
  policy.py
  response_builder.py
  prompts.py
  schemas.py
  tools/
    __init__.py
    systems.py
    inspections.py
    selfchecks.py
    toolbox.py
    ai_analysis.py
```

### 4.2 API 层

```text
backend/app/api/assistant.py
```

### 4.3 Schema 层

```text
backend/app/schemas/assistant.py
```

---

## 5. 接口设计

### 5.1 `POST /api/v1/assistant/chat`

请求：

```json
{
  "conversation_id": "optional-conv-id",
  "message": "帮我看下航班系统状态",
  "attachments": [],
  "context": {
    "page": "mobile"
  }
}
```

返回：

```json
{
  "conversation_id": "conv_xxx",
  "reply": "航班系统当前存在 2 项异常……",
  "intent": "query_system_status",
  "tool_calls": [
    {
      "tool": "get_system_status_overview",
      "arguments": {
        "system_name": "航班系统"
      }
    }
  ],
  "actions": [],
  "cards": [],
  "requires_confirmation": false,
  "pending_action": null,
  "context": {}
}
```

### 5.2 `POST /api/v1/assistant/confirm`

请求：

```json
{
  "conversation_id": "conv_xxx",
  "action_id": "act_restart_001",
  "confirmed": true
}
```

返回：

```json
{
  "conversation_id": "conv_xxx",
  "reply": "已为航班系统发起重启审批。",
  "intent": "create_restart_approval",
  "tool_calls": [],
  "actions": [],
  "cards": [],
  "requires_confirmation": false,
  "pending_action": null,
  "context": {}
}
```

---

## 6. 数据结构设计

### 6.1 AssistantChatRequest

- `conversation_id: Optional[str]`
- `message: str`
- `attachments: list`
- `context: Optional[dict]`

### 6.2 AssistantChatResponse

- `conversation_id: str`
- `reply: str`
- `intent: Optional[str]`
- `tool_calls: list`
- `actions: list`
- `cards: list`
- `requires_confirmation: bool`
- `pending_action: Optional[dict]`
- `context: dict`

### 6.3 AssistantConfirmRequest

- `conversation_id: str`
- `action_id: str`
- `confirmed: bool`

---

## 7. Tool Registry 设计

建议定义 ToolSpec：

- `name`
- `description`
- `risk_level`
- `requires_confirmation`
- `roles`
- `handler`
- `arguments_schema`

Registry 能力：

- 注册工具
- 获取工具
- 列出工具
- 判断工具是否存在

后续每增加一个能力，尽量只需要：

1. 新建 `tools/*.py`
2. 编写 handler
3. 注册 ToolSpec

---

## 8. Router 设计

V1 的 Router 先做轻量版，不做复杂 Planner。

### 8.1 Router 输出结构

```json
{
  "intent": "query_system_status",
  "tool": "get_system_status_overview",
  "arguments": {
    "system_name": "航班系统"
  }
}
```

### 8.2 V1 支持的 intent

- `query_system_status`
- `query_inspection_records`
- `query_selfcheck_records`
- `analyze_log_text`
- `create_restart_approval`
- `general_chat`

### 8.3 V1 路由策略

先采用“规则优先 + AI fallback”的方式：

1. 关键词命中已知高频意图时直接映射工具
2. 无法确定时再走 AI 意图识别
3. 若依然无法识别则退化为普通问答回复

---

## 9. Executor 设计

Executor 负责：

- 校验工具是否存在
- 校验参数
- 校验角色权限
- 判断是否需要确认
- 执行业务 handler
- 返回统一结构

统一工具执行结果建议：

```json
{
  "success": true,
  "tool": "get_system_status_overview",
  "summary": "航班系统当前存在 2 项异常",
  "data": {},
  "requires_confirmation": false
}
```

---

## 10. Context Manager 设计

V1 先用内存级/轻量级上下文结构即可，后续再增强为持久化。

至少记录：

- `conversation_id`
- 最近 20 条消息（可裁剪）
- 最近一次工具调用
- 最近聚焦的 `system_id` / `system_name`
- 最近附件引用
- 最近待确认动作

目的：支持指代解析与连续追问。

---

## 11. Policy 设计

### 11.1 风险级别

- `low`：纯查询
- `medium`：分析/生成
- `high`：会触发业务动作或配置变更

### 11.2 V1 必须确认的动作

- `create_restart_approval`
- 后续的 `update_emergency_config`

### 11.3 确认流

高风险工具在首次请求时不直接执行，而是返回：

```json
{
  "requires_confirmation": true,
  "pending_action": {
    "action_id": "act_xxx",
    "tool": "create_restart_approval",
    "arguments": {}
  }
}
```

待用户调用 confirm 接口后再执行。

---

## 12. V1 工具清单

### 12.1 systems.py

- `get_system_status_overview`
- `get_system_detail`

### 12.2 inspections.py

- `list_inspection_records`

### 12.3 selfchecks.py

- `list_selfcheck_records`

### 12.4 ai_analysis.py

- `analyze_log_text`

### 12.5 toolbox.py

- `create_restart_approval`

---

## 13. 前端 V1 要求

建议新增独立 AI 助手页面，而不是继续混在原普通问答页面中。

### 页面至少支持：

- 聊天消息区
- 输入框
- 附件上传入口（V1 可先预留）
- 动作卡片区
- 确认弹窗
- `conversation_id` 维持

### 后端 actions 返回协议示例：

```json
[
  {
    "type": "view_system",
    "label": "查看系统详情",
    "payload": {"system_id": 12}
  },
  {
    "type": "confirm_action",
    "label": "确认发起审批",
    "payload": {"action_id": "act_001"}
  }
]
```

---

## 14. 开发顺序（推荐）

### Day 1

- 建 `assistant.py` API
- 建 `assistant` 服务目录骨架
- 建 `tool_registry`
- 建基础 schema
- 接 2 个只读工具

### Day 2

- 建 router
- 建 executor
- 建 context manager
- 接查询巡检 / 自检工具
- 接日志分析工具

### Day 3

- 建 policy
- 接高风险确认流
- 接 `create_restart_approval`
- 做基础联调

### Day 4

- 接前端聊天页
- 接动作卡片和确认弹窗
- 补测试
- 清理命名和日志

---

## 15. V1 验收标准

### 后端

- 能通过 `/api/v1/assistant/chat` 进入统一助手流程
- 至少 5 个工具可正常调用
- 高风险动作能返回确认流
- confirm 接口可完成确认执行
- conversation_id 可延续上下文

### 前端

- 可发送消息
- 可看到 AI 回复
- 可点击 actions
- 可完成确认执行

### 功能层

至少能支持以下示例：

1. “帮我查今天有哪些异常系统”
2. “看看航班系统最近巡检记录”
3. “分析这段报错日志”
4. “帮我发起航班系统重启审批”
5. “确认执行”

---

## 16. 后续扩展设计预留

为了保证未来能灵活增加更多功能，V1 必须从一开始预留：

- 工具插件化注册
- 统一工具协议
- 独立 response builder
- 独立 policy 模块
- 独立 context manager
- 可扩展 actions / cards / tool_calls 结构

未来新增能力时，优先通过新增 tool 的方式扩展，而不是破坏主流程。

可扩展方向包括但不限于：

- 资产查询助手
- 监控告警助手
- 巡检计划助手
- 自检编排助手
- 应急配置助手
- 事件报告助手
- 飞书/移动端统一助手入口
- 多模型路由
- 多工具串联任务

---

## 17. 本阶段开发策略

当前阶段按以下策略执行：

1. 先完成 Assistant 后端骨架
2. 再接首批工具
3. 完成最小 API 联调
4. 再决定前端页面接入方式

先做稳的基础设施，不一开始就堆复杂 UI 和全量能力。
