# 运维助手 API 草案（v1.5 可联调）

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
  - req 中枚举约束：
    - `host_online`: normal/abnormal/unknown
    - `port_ok`: normal/abnormal/unknown
    - `last_inspection_result`: normal/abnormal/unknown
    - `last_selfcheck_result`: normal/warning/critical/unknown
  - `cpu_usage/mem_usage/disk_usage`: 0~100

## 5. 监控
- `GET /monitoring/overview`
- `GET /monitoring/rules`
- `PUT /monitoring/rules`
- `GET /monitoring/abnormal/export`

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
- `GET /admin/audit-logs?page=1&size=20&action=&username=&resource=&start_at=&end_at=&keyword=`

## 8. 健康检查
- `GET /healthz`

## 9. 错误响应约定
- 参数校验失败：
```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "errors": [ ... ]
}
```
- 认证/权限/业务错误：
```json
{
  "code": "TOKEN_EXPIRED | TOKEN_INVALID | USER_DISABLED | FORBIDDEN | HTTP_ERROR",
  "message": "具体错误信息"
}
```
