# Aegis 变更摘要（2026-03-09）

## 分支
- `feat/dameng-integration`

## 背景
本次迭代目标：
1. 将离线 AI（Ollama）接入诊断主链路，并保留规则引擎回退能力
2. 强化达梦验收闭环，覆盖关键写库接口
3. 提升可观测性，便于后续统计故障回退率与时延

---

## 变更范围

### 1) 离线 AI 接入与回退
- 接口：
  - `POST /api/v1/ai/diagnose`
  - `POST /api/v1/ai/offline/analyze`
- 策略：
  - 满足 `OFFLINE_AI_ENABLED=true && OFFLINE_AI_PROVIDER=ollama` 时优先调用本地模型
  - 调用失败或返回异常时自动回退规则引擎（`mode=rule_fallback`）
- 稳健性：
  - provider 判断大小写无关
  - LLM 未返回有效 suggestions 视为异常并触发回退

### 2) 达梦验收增强
- 脚本：`scripts/check_dm_connection.sh`
- 新增能力：
  - 在端口/迁移/健康/登录之外，增加关键写库接口验证：
    - `PUT /api/v1/auth/profile`
    - `POST /api/v1/auth/change-password`
  - 自动执行密码回滚（避免影响后续环境）
  - 支持结构化报告输出（JSON）

### 3) 可观测性增强
- 离线 AI 接口返回新增：
  - `elapsed_ms`
  - `fallback_reason`
- 审计日志同步记录以上字段，用于后续分析
- 达梦检查脚本输出 JSON 报告：
  - 成功：`ok/port/checks/checked_at`
  - 失败：`ok=false/failed_step/reason/checked_at`

### 4) 文档补充
- `docs/offline-ai-setup.md`
- `docs/login-common-pitfalls.md`
- `docs/project-progress.md`
- `docs/AGENT_CONTEXT.md`

---

## 配置项（新增）
- `OFFLINE_AI_ENABLED`
- `OFFLINE_AI_PROVIDER`
- `OFFLINE_AI_MODEL`
- `OFFLINE_AI_OLLAMA_BASE_URL`
- `OFFLINE_AI_TIMEOUT_SECONDS`

示例见：`backend/dameng.env.example`

---

## 验证建议

### A. 达梦链路
```bash
./scripts/check_dm_connection.sh 8001 /tmp/aegis_dm_check_report.json
cat /tmp/aegis_dm_check_report.json
```

### B. AI接口
1. 登录获取 token
2. 调用 `/api/v1/ai/diagnose` 与 `/api/v1/ai/offline/analyze`
3. 确认响应中包含：`mode/elapsed_ms/fallback_reason`

---

## 风险与影响

### 风险点
1. 本地 Ollama 不可达时会回退规则引擎，结果质量依赖规则库覆盖度
2. 达梦检查脚本会临时修改 admin 密码（虽然已自动回滚）
3. 观测字段新增可能影响依赖旧响应结构的客户端

### 影响面
- 后端 AI 诊断接口响应结构
- 运维验收脚本行为
- 文档与配置样例

---

## 回滚方案

### 快速回退策略
1. 将 `OFFLINE_AI_ENABLED=false`，恢复纯规则引擎
2. 回退本次分支提交（按需 `git revert`）
3. 使用旧版 `scripts/check_dm_connection.sh`（若需要避免写库检查）

### 最小化回退
- 保留文档与脚本，只关闭离线模型开关

---

## 后续建议
1. 将达梦检查 JSON 报告纳入 CI artifact
2. 增加离线 AI 回退率看板（按日统计）
3. 继续扩充规则库到 20+ 并引入误报/漏报回归样例
