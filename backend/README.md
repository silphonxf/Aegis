# Backend (FastAPI) - 可联调版

## 1) 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 配置环境变量
```bash
cp .env.example .env
```

## 3) 数据库初始化（推荐 Alembic）
```bash
alembic upgrade head
```

> 开发默认 SQLite（`DATABASE_URL=sqlite:///./aegis.db`）
> 部署时替换为达梦连接串。

## 4) 启动服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5) 默认账号
首次启动会自动初始化角色与管理员（若不存在）：
- 用户名：`admin`
- 密码：`admin123`

## 6) 常用接口
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `GET /healthz`
- 登录: `POST /api/v1/auth/login`
- 扫码解析巡检点: `GET /api/v1/inspections/points/resolve?qr_content=...`
- 巡检记录: `POST/GET /api/v1/inspections/records`
- 自检模板: `POST/GET /api/v1/selfchecks/templates`
- 自检记录: `POST/GET /api/v1/selfchecks/records`
- 报表导出: `GET /api/v1/reports/inspections/export`
- 审计日志: `GET /api/v1/admin/audit-logs`

## 7) 管理端用户创建（JSON Body）
`POST /api/v1/admin/users`
```json
{
  "username": "ops01",
  "password": "12345678",
  "role_code": "inspector"
}
```
