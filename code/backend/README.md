# Backend (FastAPI)

## 本地启动

### 方式一：使用仓库统一脚本（推荐）
在仓库根目录执行：

```bash
./scripts/dev-up.sh
```

### 方式二：手动启动

#### 1) 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 如果当前机器缺少 `python3-venv`，也可以使用用户态安装方式：
>
> ```bash
> python3 -m pip install --user --break-system-packages -r requirements.txt
> ```

#### 2) 配置环境变量
```bash
cp .env.example .env
```

至少确认以下变量：
- `SECRET_KEY`
- `INIT_ADMIN_PASSWORD`
- `DATABASE_URL`（可用 SQLite，本次也支持 MySQL）
- 如使用拆分配置，则设置 `MYSQL_HOST / MYSQL_PORT / MYSQL_NAME / MYSQL_USER / MYSQL_PASSWORD`

#### 3) 数据库初始化（Alembic）
```bash
alembic upgrade head
```

#### 4) 启动服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 统一日志格式
后端现已采用统一工程化文本日志格式：

```text
2026-05-20 09:35:12 INFO auth [req:abc123def4567890abc123def4567890] 登录成功: user=admin
```

字段顺序固定为：
- `时间`：`YYYY-MM-DD HH:mm:ss`
- `日志级别`：`DEBUG / INFO / WARNING / ERROR / CRITICAL`
- `模块`：如 `auth` / `access` / `health` / `app`
- `请求 ID`：`[req:<32位小写十六进制uuid>]`
- `日志内容`

说明：
- 每个 HTTP 请求进入后端时都会绑定一个统一格式的 `request_id`
- 若客户端传入 `X-Request-ID`，只有当它是合法 32 位十六进制字符串（或标准 UUID 去掉连字符后）才会被沿用
- 否则后端自动生成新的 32 位小写十六进制 UUID
- 响应头会返回 `X-Request-ID`
- 常规错误响应体也会附带 `request_id`

## 启动后的默认行为
- 后端启动时会自动补齐最小种子数据：
  - 角色（`inspector/admin/super_admin`）
  - 默认管理员 `admin`
  - 示例系统
  - 示例巡检点

## MySQL 配置说明
- 完整连接串示例：`mysql+pymysql://user:password@127.0.0.1:3306/aegis?charset=utf8mb4`
- 也可参考 `mysql.env.example` 使用 `MYSQL_*` 拆分配置，后端会自动拼接连接串
- 本地测试仍默认使用 SQLite；切换 MySQL 后执行 `alembic upgrade head` 初始化表结构

## 本地默认账号
- `admin / local_admin_pass_2026`

## 常用检查
```bash
./scripts/dev-check.sh http://127.0.0.1:8000 admin local_admin_pass_2026
./scripts/iteration3_smoke.sh http://127.0.0.1:8000 admin local_admin_pass_2026
```

## 当前已覆盖的关键接口测试
- auth：登录、获取用户、修改资料、修改密码
- inspections：巡检点解析、巡检记录创建/查询
- selfchecks：模板、自检记录、简化自检
- toolbox：ping、port-check、任务创建、状态流转
- ai：诊断、离线分析、历史查询
- admin：系统、资产、审计日志

## 关键接口
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `PUT /api/v1/auth/profile`
- `POST /api/v1/auth/change-password`
- `GET /api/v1/inspections/points/resolve`
- `POST/GET /api/v1/inspections/records`
- `POST/GET /api/v1/selfchecks/templates`
- `POST/GET /api/v1/selfchecks/records`
- `GET /api/v1/monitoring/overview`
- `GET/PUT /api/v1/monitoring/rules`
- `GET /api/v1/admin/audit-logs`
- `POST /api/v1/ai/diagnose`
- `POST /api/v1/ai/offline/analyze`
