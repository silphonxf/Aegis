# Notes

## Product Direction

系统自检模块目标不是单纯新增一个记录列表，而是把“谁负责哪个系统、系统最近是否自检、异常后如何处置”放在同一个管理端工作流里。

数据库自检作为系统自检的一个专门配置视图处理。第一版沿用 `systems` 表保存数据库目标，把 MySQL 连接参数写入 `selfcheck_skill`，让现有后端 `_extract_mysql_config` 和 `_run_mysql_selfcheck_report` 继续工作。

## Existing Backend Surface

- `GET /api/v1/selfchecks/status`
- `GET /api/v1/selfchecks/run`
- `GET /api/v1/selfchecks/reports`
- `GET /api/v1/selfchecks/reports/{file_name}`
- `GET /api/v1/selfchecks/templates`
- `POST /api/v1/selfchecks/templates`
- `POST /api/v1/selfchecks/records`
- `POST /api/v1/selfchecks/records/simple`
- `GET /api/v1/selfchecks/records`
- `GET /api/v1/admin/systems`
- `POST /api/v1/admin/systems`
- `PUT /api/v1/admin/systems/{system_id}`
- `PATCH /api/v1/admin/systems/{system_id}/active`

## Database Selfcheck Skill Shape

管理端数据库配置保存时生成的 `selfcheck_skill` 应包含这些可解析字段：

```text
MySQL 数据库自检
host=127.0.0.1
port=3306
database=aegis
user=aegis_monitor
password=******
```

后端当前支持从 `host`、`port`、`database/db/dbname`、`user/username`、`password/pwd` 等字段解析连接参数。

## Design Anchors

- 管理端目标布局参考 `docs/emergency-ops-admin-design.md` 的“Tab 1：系统自检配置与记录”。
- 数据模型参考 `docs/shared-data-model-v1.md` 中 `selfcheck_records` 和自检模板部分。
- 移动端现有 AI 自检交互可作为管理端接入逻辑参照。

## Open Questions

- 自检负责人当前是否已有正式字段，还是需要先复用系统负责人字段。
- 运行服务器来源应优先使用现有 `systems.host_address`，还是等服务器基础 IP 模块补齐后再做多选。
- Runbook 联动入口第一版是简单跳转，还是直接创建处置动作或审批记录。
- 数据库密码第一版随 `selfcheck_skill` 保存；后续应评估迁移到加密字段或密钥管理。
