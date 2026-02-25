# Aegis 迭代3验收清单（工具箱 + AI诊断）

## 0. 环境准备

```bash
cd /home/xf/.openclaw/workspace/code/aegis/backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd /home/xf/.openclaw/workspace/code/aegis/frontend-mobile
python3 -m http.server 5173

cd /home/xf/.openclaw/workspace/code/aegis/frontend-admin
python3 -m http.server 5174
```

---

## 1. 工具箱 API 验收

- [ ] `POST /api/v1/toolbox/ping` 返回 `ok/latency_ms/output`
- [ ] `POST /api/v1/toolbox/port-check` 返回 `ok/latency_ms/error`
- [ ] `POST /api/v1/toolbox/restart-task` 创建 `pending_approval` 任务
- [ ] `GET /api/v1/toolbox/tasks` 可分页查询
- [ ] `GET /api/v1/toolbox/tasks?status=pending_approval` 可按状态筛选
- [ ] `PUT /api/v1/toolbox/tasks/{id}/status` 支持状态流：
  - `pending_approval -> approved`
  - `pending_approval -> rejected`
  - `approved -> done`
- [ ] 非法状态跳转返回 `TASK_STATUS_INVALID`

---

## 2. AI 诊断 API 验收

- [ ] `POST /api/v1/ai/diagnose` 返回 mock 建议并落库
- [ ] `GET /api/v1/ai/diagnoses` 返回历史记录
- [ ] `GET /api/v1/ai/diagnoses?severity=high` 可按严重级别筛选

---

## 3. 移动端验收（5173）

- [ ] 登录成功
- [ ] 工具箱：Ping / 端口检测 / 创建重启任务
- [ ] 工具任务：可刷新列表、可更新状态
- [ ] AI诊断：可生成建议
- [ ] AI历史：可按当前 severity 查看记录

---

## 4. 管理端验收（5174）

- [ ] 工具任务审批区可查看任务并变更状态
- [ ] AI诊断记录区可筛选并查看详情
- [ ] 审计日志可看到：
  - `toolbox_ping`
  - `toolbox_port_check`
  - `toolbox_create_restart_task`
  - `toolbox_update_task_status`
  - `ai_diagnose`

---

## 5. 回归项（迭代1/2）

- [ ] 巡检提报/历史正常
- [ ] 自检提报/历史正常
- [ ] 监控看板（系统+资产）正常
- [ ] 本机监控采集正常
- [ ] 资产筛选/导出正常
- [ ] CORS 无跨域报错
