# System Selfcheck Module

## Goal

围绕“系统自检模块”建立后续迭代 thread，把系统配置、数据库自检配置、自检负责人、自检记录、AI 自检报告和异常联动预案收拢到同一个管理端工作流中。

## Current State

- 后端已有自检模板、自检记录、系统自检状态、AI 自检报告等接口。
- 后端已有 MySQL 数据库自检采集逻辑，会从 `selfcheck_skill` 中解析主机、端口、库名、用户和密码。
- 移动端已有“系统自检”入口，可选择系统、查看状态、生成 AI 自检报告、查看历史报告。
- 管理端需要新增“数据库自检配置”，仿照系统配置维护数据库连接和自检要求。
- 管理端设计文档已将“系统自检配置与记录”定义为“资产与日常运维看板”的第一个 Tab。
- 当前 thread 先作为系统自检模块的承接点，后续逐项拆分管理端页面、数据联动和接口补齐。

## Key Files

- `docs/emergency-ops-admin-design.md`
- `docs/shared-data-model-v1.md`
- `docs/api-spec-v1.md`
- `code/backend/app/api/selfchecks.py`
- `code/backend/app/models/selfcheck.py`
- `code/backend/app/schemas/selfcheck.py`
- `code/frontend-mobile/app.js`
- `code/frontend-admin/index.html`
- `code/frontend-admin/app.js`
- `code/frontend-admin/js/database-selfchecks.js`

## Decisions

- 先按现有后端接口推进管理端系统自检页面，避免过早改动数据模型。
- 系统自检模块优先形成闭环：系统信息、运行服务器、自检负责人、最近记录、AI 自检报告、异常处置入口。
- AI 自检继续复用 `/api/v1/selfchecks/status`、`/api/v1/selfchecks/run` 和报告接口。
- 数据库自检第一版不新增后端表，复用 `systems` 记录和 `selfcheck_skill` 承载 MySQL 连接配置。
- 数据库配置在管理端单独成页，保存时生成可被后端解析的 MySQL 自检 skill。
- 手工填报记录继续复用 `/api/v1/selfchecks/records` 与 `/api/v1/selfchecks/records/simple`。
- 管理端页面保持和现有模块一致的轻量样式，不单独引入新的前端框架。

## Next Steps

- 梳理管理端当前自检相关入口，确认是否已有分散页面需要合并。
- 新增或调整“系统自检配置与记录”页面。
- 新增“数据库自检配置”页面，仿照系统配置支持新增、编辑、停用和查询。
- 在系统列表中展示最近自检状态、最近填报时间、自检负责人和运行服务器。
- 在数据库配置中维护数据库类型、主机、端口、库名、用户名、密码、检查频次和自检要求。
- 在记录区支持按系统、结果、时间范围筛选。
- 接入 AI 自检报告生成和历史报告查看。
- 评估异常记录跳转 Runbook 的最小实现方式。

## Handoff

继续本 thread 时，优先从管理端信息架构入手：先让“系统自检配置与记录”可见且能读取现有数据，再补负责人、服务器、Runbook 联动等字段和动作。
