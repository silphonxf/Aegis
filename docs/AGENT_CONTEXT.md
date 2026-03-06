# Aegis 持久化上下文（给我下次快速接入）

> 最后更新：2026-03-06  
> 用途：避免每次都从零了解项目进度，5分钟内恢复工作上下文。

## 1. 项目定位

Aegis 是一个运维助手系统，包含：
- 移动端（巡检、自检、报表）
- 管理后台（看板、资产、规则、审计、审批）
- 后端 API（Python）
- 达梦数据库适配（含连接、迁移、验证脚本）

仓库：`git@github.com:silphonxf/Aegis.git`

## 2. 当前里程碑状态

- 产品里程碑：`v1.0.0` 已完成（见 `README.md`）
- 近阶段重点：达梦数据库接入可用性与验收闭环
- 已有进度文档：`docs/project-progress.md`

## 3. 关键结论（重要）

1. 达梦支持两种配置：
   - `DATABASE_URL`
   - `DM_HOST/DM_PORT/DM_NAME/DM_USER/DM_PASSWORD`（优先级更高）

2. 达梦一键检查脚本已存在：
   - `scripts/check_dm_connection.sh`

3. 本地验证过的检查链路：
   - 端口连通
   - Alembic 升级
   - 后端启动
   - `/healthz`
   - `/api/v1/auth/login`

## 4. 关键文件地图（下次优先看）

### 业务总览
- `README.md`
- `docs/project-progress.md`
- `docs/release-v1.0.0.md`

### 达梦接入
- `docs/dameng-setup.md`
- `backend/dameng.env.example`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/alembic/env.py`
- `scripts/check_dm_connection.sh`

### 验收与联调
- `docs/iteration3-acceptance.md`
- `docs/release-checklist-v1.0.0-admin-v2.md`
- `docs/integration-quickstart.md`

## 5. 下次会话“快速恢复”步骤（固定流程）

每次接手 Aegis，按下面 6 步走：

1. `git -C code/aegis status -sb` 看分支与脏区
2. 读 `docs/AGENT_CONTEXT.md`（本文件）
3. 读 `docs/project-progress.md` 获取最新进展
4. 按任务类型打开相关文档（达梦/前端/验收）
5. 如需环境验证：执行 `./scripts/check_dm_connection.sh`
6. 变更后更新本文件“7. 最近更新记录”

## 6. 当前建议待办（可滚动维护）

- [x] 达梦接入加入 CI 可选检查（环境变量开关）
- [ ] 关键写库接口补充达梦集成测试
- [ ] 登录常见误区文档补充（应用账号 vs 数据库账号）

## 7. 最近更新记录（倒序）

### 2026-03-06
- 移动端自检-系统状态页新增系统选择框（支持按系统查看CPU/MEM/DISK）
- 同步时间：2026-03-06 13:46:23 +0800
- 接续开发：新增 CI 工作流 `.github/workflows/backend-ci.yml`
- 默认跑 SQLite 冒烟检查（迁移 + 启动 + healthz）
- 新增达梦可选检查开关：`workflow_dispatch.run_dm_check` 或仓库变量 `RUN_DM_CHECK=true`
- 同步时间：2026-03-06 13:40 +0800
- 新增一键同步命令
- 同步时间：2026-03-06 11:58:55 +0800
- 新增本持久化上下文文件 `docs/AGENT_CONTEXT.md`
- 目标：让后续会话无需重复“重新了解项目”
- 与用户约定：后续每次有关键进展，都同步更新本文件

---

## 8. 给未来自己的提醒

- 若用户说“看下 Aegis 进度”，先读本文件再回答。
- 回答要优先给：当前状态 + 本次可执行动作 + 风险点。
- 不要只口头记忆，任何关键结论都写回本文件。
