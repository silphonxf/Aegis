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

## 4) 访问
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/healthz
