# 运维助手 API 草案（v1）

Base URL: `/api/v1`

## 1. 认证
- `POST /auth/login`
  - req: { username, password }
  - resp: { access_token, token_type }

- `GET /auth/me`
  - resp: 当前用户信息

## 2. 巡检
- `POST /inspections/records`
  - req: { system_id, point_id, result, note, inspected_at }
- `GET /inspections/records`
  - query: system_id, result, start_at, end_at, page, size

## 3. 自检
- `GET /selfchecks/templates`
- `POST /selfchecks/templates`（admin/super_admin）
- `POST /selfchecks/records`
  - req: { system_id, template_id, result, summary, checked_at }
- `GET /selfchecks/records`

## 4. 系统状态
- `GET /systems/status/overview`
  - 返回系统最新状态快照（绿/黄/红统计 + 列表）
- `POST /systems/{system_id}/status/snapshot`
  - 采集或上报状态快照

## 5. 报表
- `GET /reports/inspections`
- `GET /reports/selfchecks`
- `GET /reports/inspections/export`（CSV）
- `GET /reports/selfchecks/export`（CSV）

## 6. 管理
- `GET /admin/users`
- `POST /admin/users`
- `PATCH /admin/users/{id}/status`
- `GET /admin/systems`
- `POST /admin/systems`

## 7. 健康检查
- `GET /healthz`

