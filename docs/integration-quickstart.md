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

移动端可测：
- 登录
- 扫码解析巡检点
- 提交巡检记录
- 提交自检记录
- 巡检历史查询
- 自检历史查询

## 3. 启动后台联调页
```bash
cd frontend-admin
python3 -m http.server 5174
```
访问：`http://127.0.0.1:5174`

后台可测：
- 登录
- 创建用户
- 创建系统
- 创建自检模板
- 查看系统总览
- 查看审计日志
- 状态规则本地配置（占位，后续接后端）

## 4. 默认账号
- admin / admin123

## 5. 推荐联调顺序
1) 后台创建系统和自检模板
2) 移动端扫码提交巡检
3) 移动端提交自检
4) 后台查看状态总览和审计日志
