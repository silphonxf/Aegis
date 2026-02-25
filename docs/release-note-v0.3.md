# Aegis 发布说明 v0.3（迭代1~3）

## 版本概览

- 范围：迭代1（MVP闭环）+ 迭代2（管理与可视化）+ 迭代3（工具箱与AI诊断mock）
- 目标状态：可演示、可联调、可回归

---

## 里程碑状态

### 迭代1（MVP核心闭环）✅

- 登录认证（JWT）与 RBAC
- 巡检：扫码解析、记录提交、历史查询
- 自检：模板创建、记录提交、历史查询
- 报表：巡检/自检查询 + CSV导出 + 时间筛选
- 审计日志：关键操作记录与筛选查询

### 迭代2（管理与可视化）✅

- 管理后台：用户/系统/模板管理（创建+列表）
- 全局看板：系统状态聚合（红黄绿）
- 监控规则：阈值读取/保存
- 资产管理：单条创建、批量导入、筛选查询、CSV导出
- 本机采集样本：一键采集当前主机并入看板
- 监控快照：持久化 CPU/MEM/DISK 百分比 + 等级

### 迭代3（增强能力）进行中（已完成第一阶段）🟡

- 移动端工具箱：Ping、端口检测、重启任务（审批mock）
- 工具任务流转：pending_approval -> approved/rejected -> done
- AI诊断mock：建议生成 + 历史落库 + 筛选查询
- 管理端与移动端均已提供迭代3入口

> 说明：NFC、真实远程重启执行、离线AI模型推理引擎仍在后续范围。

---

## 关键接口清单（摘要）

### 认证
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### 巡检 / 自检
- `GET /api/v1/inspections/points/resolve`
- `POST /api/v1/inspections/records`
- `GET /api/v1/inspections/records`
- `POST /api/v1/selfchecks/templates`
- `GET /api/v1/selfchecks/templates`
- `POST /api/v1/selfchecks/records`
- `GET /api/v1/selfchecks/records`

### 监控 / 看板
- `GET /api/v1/monitoring/overview`
- `GET /api/v1/monitoring/rules`
- `PUT /api/v1/monitoring/rules`
- `POST /api/v1/monitoring/collect/local`
- `GET /api/v1/monitoring/abnormal/export`
- `POST /api/v1/systems/{system_id}/status/snapshot`

### 管理 / 资产 / 审计
- `GET/POST /api/v1/admin/users`
- `GET/POST /api/v1/admin/systems`
- `GET /api/v1/admin/audit-logs`
- `GET/POST /api/v1/admin/assets`
- `POST /api/v1/admin/assets/batch`
- `GET /api/v1/admin/assets/export`
- `GET /api/v1/admin/assets/summary`

### 工具箱 / AI（迭代3）
- `POST /api/v1/toolbox/ping`
- `POST /api/v1/toolbox/port-check`
- `POST /api/v1/toolbox/restart-task`
- `GET /api/v1/toolbox/tasks`
- `PUT /api/v1/toolbox/tasks/{task_id}/status`
- `POST /api/v1/ai/diagnose`
- `GET /api/v1/ai/diagnoses`

---

## 验证与测试

- 迭代3验收清单：`docs/iteration3-acceptance.md`
- 一键冒烟脚本：`scripts/iteration3_smoke.sh`

```bash
cd /home/xf/.openclaw/workspace/code/aegis
./scripts/iteration3_smoke.sh
```

---

## 已知限制

1. 工具箱“重启任务”当前为审批mock，不执行真实系统重启。
2. AI诊断当前为规则+模板mock，不调用外部模型。
3. 本机监控采集当前基于Linux `/proc` 与本机端口探测。
4. 历史数据库若未按迁移链初始化，可能需要做一次兼容补列。

---

## 下一步建议（迭代3第二阶段）

1. 将重启任务接入真实执行器（带审批与回滚保护）。
2. 增加工具任务执行日志与状态回调（running/success/failed）。
3. AI诊断接入可配置模型网关（保留mock兜底）。
4. 增加多主机采集（SSH/Agent）与主机凭据管理。
5. 增加自动化回归（pytest + API contract tests）。
