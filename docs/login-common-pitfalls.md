# Aegis 登录常见误区（应用账号 vs 数据库账号）

## 结论先说
- `POST /api/v1/auth/login` 使用的是 **Aegis 应用账号**（默认 `admin/admin123`）
- 不是达梦数据库账号（如 `SYSDBA` / `DM_USER`）

---

## 常见误区 1：拿数据库账号去调用登录接口

**错误示例：**
- 用户名：`SYSDBA`
- 密码：数据库口令

**结果：**
- 返回 `401 AUTH_INVALID`

**原因：**
- 登录接口校验的是 `users` 表中的应用用户，而不是数据库连接用户。

---

## 常见误区 2：以为改了 `DM_USER` 就能登录后台

`DM_USER/DM_PASSWORD` 仅用于后端连接数据库，不影响 Aegis 后台登录凭据。

---

## 正确排查顺序

1. 先确认后端和数据库连通（`/healthz`）
2. 使用应用账号登录（默认 `admin/admin123`）
3. 若失败，检查是否曾改过应用密码（`/auth/change-password`）
4. 再检查 users 表是否存在目标账号且 `is_active=true`

---

## 与达梦验收脚本的对应关系

`./scripts/check_dm_connection.sh` 已包含：
- 登录验证（应用账号）
- 写库接口验证：
  - `PUT /api/v1/auth/profile`
  - `POST /api/v1/auth/change-password`（含回滚）

这用于确认“数据库连接正常 + 关键写库接口可用”。
