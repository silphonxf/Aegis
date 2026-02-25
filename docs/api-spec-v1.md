# 运维助手 API 草案（v1.2 可联调）

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
- `POST /systems/{system_id}/status/snapshot?status_color=green`

## 5. 监控（新增）
- `GET /monitoring/overview`（总览 + 异常列表）
- `GET /monitoring/rules`（读取阈值规则）
- `PUT /monitoring/rules`（更新阈值规则，super_admin）

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
