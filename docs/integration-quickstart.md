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

## 5. 联调主流程
1) 登录
2) 扫码解析巡检点（QR://DEMO-SYS-001/P-001）
3) 提交巡检记录
4) 提交自检记录（先在后台创建模板）
5) 查看系统总览与审计日志
