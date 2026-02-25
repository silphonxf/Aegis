# Aegis 联调快速开始

## 1. 启动后端
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2. 启动移动端联调页
```bash
cd frontend-mobile
python3 -m http.server 5173
```
访问：`http://127.0.0.1:5173`

## 3. 启动后台联调页
```bash
cd frontend-admin
python3 -m http.server 5174
```
访问：`http://127.0.0.1:5174`

## 4. 默认账号
- admin / admin123

## 5. 推荐联调顺序
1) 后台创建系统和自检模板
2) 移动端扫码提交巡检
3) 移动端提交自检
4) 后台查看监控总览（`/monitoring/overview`）
5) 后台读取/更新状态规则（`/monitoring/rules`）
6) 后台查看审计日志
