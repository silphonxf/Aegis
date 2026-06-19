# Aegis 文档索引（精简版）

为减少阶段性重复文档，本目录统一以“长期有效文档”为主。

## 核心文档（保留）

- `AGENT_CONTEXT.md`
  - 给 Agent 的持续上下文（最新决策、关键变更、当前重点）
- `project-progress.md`
  - 项目进展主记录（阶段成果持续累积）
- `api-spec-v1.md`
  - API 规范
- `er-model.md`
  - 数据模型设计
- `integration-quickstart.md`
  - 联调与快速启动说明
- `offline-ai-setup.md`
  - 离线 AI（Ollama）安装与接入
- `openclaw-ai-provider-design.md`
  - Aegis 对接 OpenClaw 的 AI provider 技术设计（第一版）
- `openclaw-ai-adapter-local-dev.md`
  - 本地 OpenClaw AI Adapter 联调说明（第一版）
- `login-common-pitfalls.md`
  - 登录常见误区（应用账号 vs 数据库账号）
- `phase1-development-plan.md`
  - 第一阶段开发计划（测试护栏、本地体验、工具箱闭环、后台轻模块化）
- `aegis-assistant-v1-development-plan.md`
  - AI 助手 V1 开发原则与工具化方案
- `emergency-ops-admin-design.md`
  - 管理端业务闭环、权限隔离和审计原则
- `log-scope-access-design.md`
  - 日志可见范围与管理端配置设计
- `system-status-management-design.md`
  - 系统状态管理端配置设计
- `shared-data-model-v1.md`
  - 共享主数据模型草案
- `shared-data-migration-plan-v1.md`
  - 共享主数据迁移方案
- `scripts-inventory.md`
  - `scripts/` 目录脚本用途与后续清理建议

## 清理策略

已删除“阶段性重复文档/里程碑快照文档”，避免同一信息在多处分叉维护：

- 迭代发布说明类（如 `release-note-v0.3.md`, `release-v1.0.0.md`）
- 阶段验收清单快照（如 `iteration3-acceptance.md`, `release-checklist-v1.0.0-admin-v2.md`）
- 单次优化总结（如 `admin-ui-optimization-summary-2026-03-01.md`）
- 单次分支变更摘要
- 早期阶段开发计划草案（如 `development-plan.md`）
- 已完成的历史里程碑范围文档（如 `mvp-scope.md`）
- 已落地的单端实施方案（如管理端 V2 前端实施、移动端 UI 重构方案）

后续若有阶段总结，请优先更新：
- `project-progress.md`（对外可读主进度）
- `AGENT_CONTEXT.md`（给 Agent 快速恢复上下文）
