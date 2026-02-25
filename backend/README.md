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

## 3) 数据库初始化（Alembic）
```bash
alembic upgrade head
```

## 4) 启动服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5) 默认账号
- admin / admin123

## 6) 关键接口
- `POST /api/v1/auth/login`
- `GET /api/v1/inspections/points/resolve`
- `POST/GET /api/v1/inspections/records`
- `POST/GET /api/v1/selfchecks/templates`
- `POST/GET /api/v1/selfchecks/records`
- `GET /api/v1/monitoring/overview`
- `GET/PUT /api/v1/monitoring/rules`
- `GET /api/v1/admin/audit-logs`
