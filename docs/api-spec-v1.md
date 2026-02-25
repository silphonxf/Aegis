# 运维助手 API 草案（v1.1 可联调）

Base URL: `/api/v1`

## 1. 认证
- `POST /auth/login`
  - req: `{ username, password }`
  - resp: `{ access_token, token_type }`
- `GET /auth/me`

## 2. 巡检
- `GET /inspections/points/resolve?qr_content=...`（扫码内容解析巡检点）
- `POST /inspections/records`
  - req: `{ system_id, point_id, result, note, inspected_at }`
- `GET /inspections/records`
  - query: `system_id, result, start_at, end_at, page, size`

## 3. 自检
- `GET /selfchecks/templates?page=1&size=20`
- `POST /selfchecks/templates`（admin/super_admin）
- `POST /selfchecks/records`
  - req: `{ system_id, template_id, result, summary, checked_at }`
- `GET /selfchecks/records`
  - query: `system_id, result, start_at, end_at, page, size`

## 4. 系统状态
- `GET /systems/status/overview`
- `POST /systems/{system_id}/status/snapshot?status_color=green`

## 5. 报表
- `GET /reports/inspections`
- `GET /reports/selfchecks`
- `GET /reports/inspections/export`（CSV）
- `GET /reports/selfchecks/export`（CSV）

## 6. 管理
- `GET /admin/users?page=1&size=20`
- `POST /admin/users`
  - req(JSON): `{ username, password, role_code }`
- `GET /admin/systems?page=1&size=20`
- `POST /admin/systems`
- `GET /admin/audit-logs?page=1&size=20`

## 7. 健康检查
- `GET /healthz`
