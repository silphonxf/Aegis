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
- `DATABASE_URL`（本地默认 SQLite）

#### 3) 数据库初始化（Alembic）
```bash
alembic upgrade head
```

#### 4) 启动服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 启动后的默认行为
- 后端启动时会自动补齐最小种子数据：
  - 角色（`inspector/admin/super_admin`）
  - 默认管理员 `admin`
  - 示例系统
  - 示例巡检点

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
