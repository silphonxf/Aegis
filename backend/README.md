# Backend (FastAPI)

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

## 3) 启动
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4) 默认账号
首次启动会自动建表并初始化：
- 用户名：`admin`
- 密码：`admin123`

## 5) API
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/healthz

## 6) 达梦适配
开发默认 SQLite。部署时将 `.env` 中 `DATABASE_URL` 改为达梦连接串，例如：

```env
DATABASE_URL=dm+dmPython://SYSDBA:SYSDBA@127.0.0.1:5236/MAIN
```
