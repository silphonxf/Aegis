# Aegis 项目进度（更新于 2026-02-28）

## 当前总体状态

- 已完成：v1.0.0 正式版范围（认证、巡检、自检、报表、管理看板、资产管理、审计、工具箱与审批流基础能力）
- 当前重点：达梦数据库接入完善与一键验收

## 本次新增进展（达梦接入）

### 1) 配置能力增强

已支持两种达梦配置方式：

- 方式A：`DATABASE_URL` 完整连接串
- 方式B：`DM_HOST/DM_PORT/DM_NAME/DM_USER/DM_PASSWORD` 拆分配置（优先级高于 `DATABASE_URL`）

涉及文件：

- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/alembic/env.py`
- `backend/dameng.env.example`
- `docs/dameng-setup.md`

### 2) 一键检查脚本

新增脚本：`scripts/check_dm_connection.sh`

脚本会自动执行：

1. 达梦端口连通检查（127.0.0.1:5236）
2. Alembic 迁移（`alembic upgrade head`）
3. 后端启动
4. `/healthz` 健康检查
5. 登录检查（`/api/v1/auth/login`）

使用方式：

```bash
cd /home/xf/.openclaw/workspace/code/aegis
./scripts/check_dm_connection.sh        # 默认 8001
./scripts/check_dm_connection.sh 8002   # 指定端口
```

### 3) 本地验证结果

在本机环境实测通过：

- 达梦端口可达
- Alembic 迁移成功
- `/healthz` 返回 `{"status":"ok"}`
- admin 登录返回 `access_token`

## 下一步建议

1. 对关键写库接口补充达梦下的集成测试用例
2. 增加“常见登录误区”说明（区分应用 admin 与数据库账号）
3. 离线规则库从当前 6 条扩充到 20+ 条，并补充误报/漏报回归样例

## 本次新增进展（2026-03-06）

### 4) CI 已接入 + 达梦可选检查

已新增 GitHub Actions 工作流：

- `.github/workflows/backend-ci.yml`

默认行为：
- 在 `push/pull_request`（backend 相关路径）时运行 SQLite 冒烟检查：
  - 安装依赖
  - Alembic 迁移
  - 启动 API
  - `GET /healthz`

可选行为（按需开启达梦检查）：
- 手动触发 `workflow_dispatch` 时将 `run_dm_check=true`
- 或设置仓库变量 `RUN_DM_CHECK=true`
- 达梦连接参数走 `secrets`（`DM_HOST/DM_PORT/DM_NAME/DM_USER/DM_PASSWORD`）
- 调用 `scripts/check_dm_connection.sh` 执行完整达梦连通检查

### 5) AI离线错误日志分析（Phase 1 MVP）

已新增离线分析数据模型与接口（规则引擎版本）：

- 新增表：
  - `offline_analysis_tasks`
  - `offline_analysis_results`
- Alembic：`backend/alembic/versions/20260306_09_offline_analysis_tables.py`
- 新增模型：`backend/app/models/offline_analysis.py`
- 新增接口（`/api/v1/ai/offline/*`）：
  - `POST /api/v1/ai/offline/analyze`
  - `GET /api/v1/ai/offline/tasks`
  - `GET /api/v1/ai/offline/tasks/{task_id}`

规则引擎能力（首版）：
- 内置 6 条高频规则（数据库连接失败、磁盘满、OOM、端口冲突、鉴权失败、超时）
- 输出：命中规则、风险等级、摘要、处置建议、日志摘录
- 已本地联调验证通过（admin 登录后可调用离线分析接口）
