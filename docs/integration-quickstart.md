# Aegis 联调快速开始

## 1. 推荐方式：使用统一脚本启动
在仓库根目录执行：

```bash
cd /home/xf/.openclaw/workspace/projects/Aegis
./scripts/dev-up.sh
```

启动完成后默认访问：
- 后端：`http://127.0.0.1:8000`
- 移动端：`http://127.0.0.1:5173`
- 管理后台：`http://127.0.0.1:5174`

默认管理员：
- `admin / local_admin_pass_2026`

> 说明：后端启动时会自动补齐最小种子数据（角色、默认管理员、示例系统/巡检点），首次本地联调可直接登录。

---

## 2. 手动启动后端
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 按需修改 SECRET_KEY / INIT_ADMIN_PASSWORD
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

如果当前机器没有 `python3-venv`，也可以临时使用：

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

## 3. 启动移动端联调页
```bash
cd frontend-mobile
python3 -m http.server 5173
```
访问：`http://127.0.0.1:5173`

## 4. 启动后台联调页
```bash
cd frontend-admin
python3 -m http.server 5174
```
访问：`http://127.0.0.1:5174`

## 5. 常用开发脚本

### 停止服务
```bash
./scripts/dev-stop.sh
```

### 查看状态
```bash
./scripts/dev-status.sh
```

### 重置本地环境
```bash
./scripts/dev-reset.sh
```

### 基础检查
```bash
./scripts/dev-check.sh http://127.0.0.1:8000 admin local_admin_pass_2026
```

### 完整冒烟
```bash
./scripts/iteration3_smoke.sh http://127.0.0.1:8000 admin local_admin_pass_2026
```

## 6. 推荐联调顺序
1. 后台创建系统和自检模板
2. 移动端扫码提交巡检
3. 移动端提交自检
4. 后台查看监控总览（`/monitoring/overview`）
5. 后台读取/更新状态规则（`/monitoring/rules`）
6. 后台查看审计日志
7. 跑一遍 `dev-check.sh` 或 `iteration3_smoke.sh`

## 7. 局域网 HTTPS 启动（推荐用于相机/NFC调试）
```bash
./scripts/start_lan_https.sh
```

启动后示例：
- `https://<LAN_IP>:5173`（移动端）
- `https://<LAN_IP>:5174`（后台）
- `https://<LAN_IP>:8000`（后端）

> 首次访问需信任自签名证书，否则浏览器可能继续拦截相机/NFC能力。

## 8. 联调补充说明
- 前端 API 地址建议填当前页面主机的 `:8000`
- 本地联调默认走 SQLite，可按需切换 MySQL。
- 离线 AI 接入见 `docs/offline-ai-setup.md`
