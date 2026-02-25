# 运维助手 API 草案（v1.4 可联调）

Base URL: `/api/v1`

## 1. 认证
- `POST /auth/login`
- `GET /auth/me`

## 2. 巡检
- `GET /inspections/points/resolve?qr_content=...`
- `POST /inspections/records`
- `GET /inspections/records?system_id=&page=&size=`

## 3. 自检
- `GET /selfchecks/templates?page=1&size=20`
- `POST /selfchecks/templates`
- `POST /selfchecks/records`
- `GET /selfchecks/records?system_id=&page=&size=`

## 4. 系统状态
- `GET /systems/status/overview`
- `POST /systems/{system_id}/status/snapshot`
  - req:
  ```json
  {
    "host_online": "normal",
    "port_ok": "normal",
    "cpu_usage": 68,
    "mem_usage": 72,
    "disk_usage": 80,
    "last_inspection_result": "normal",
    "last_selfcheck_result": "warning"
  }
  ```
  - resp: 自动计算 `cpu_level/mem_level/disk_level` 与 `status_color`

## 5. 监控
- `GET /monitoring/overview`（总览 + 异常列表）
- `GET /monitoring/rules`（读取阈值规则）
- `PUT /monitoring/rules`（更新阈值规则，super_admin）
- `GET /monitoring/abnormal/export`（导出异常清单 CSV）

## 6. 报表
- `GET /reports/inspections`
- `GET /reports/selfchecks`
- `GET /reports/inspections/export`
- `GET /reports/selfchecks/export`

## 7. 管理
- `GET /admin/users?page=1&size=20`
- `POST /admin/users`
- `GET /admin/systems?page=1&size=20`
- `POST /admin/systems`
- `GET /admin/audit-logs?page=1&size=20`

## 8. 健康检查
- `GET /healthz`
