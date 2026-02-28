# 达梦数据库接入说明（本机）

## 1. 前置条件

- 已安装并启动达梦数据库实例
- 能使用 DBA 账号执行 SQL（如 `SYSDBA`）
- 已安装达梦 Python 驱动与 SQLAlchemy 方言（按你本机环境）

## 2. 创建业务用户

执行：`scripts/dameng_init.sql`

> 本仓库已提供脚本：`/scripts/dameng_init.sql`

## 3. 配置后端连接

复制并修改环境文件：

```bash
cd backend
cp dameng.env.example .env
```

核心配置（二选一）：

```env
# 方案 A：完整连接串
DATABASE_URL=dm+dmPython://AEGIS_USER:StrongPass_123@127.0.0.1:5236/AEGIS

# 方案 B：拆分字段（配置了 DM_* 时会优先于 DATABASE_URL）
DM_HOST=127.0.0.1
DM_PORT=5236
DM_NAME=AEGIS
DM_USER=AEGIS_USER
DM_PASSWORD=StrongPass_123
```

## 4. 迁移建表

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

## 5. 启动服务

推荐直接用脚本（已包含 `LD_LIBRARY_PATH`）：

```bash
cd /home/xf/.openclaw/workspace/code/aegis
./scripts/run_backend_dm.sh
```

或手工启动：

```bash
export LD_LIBRARY_PATH=/data/DMdata/dmdbms/drivers/dpi:/data/DMdata/dmdbms/drivers/dpi/dependencies:$LD_LIBRARY_PATH
uvicorn app.main:app --reload --port 8000
```

## 6. 验证

- `GET /healthz` 正常
- 登录、巡检、资产创建均可落库

## 备注

若你本机尚未安装达梦 Python 方言/驱动，请先安装后再执行迁移。
