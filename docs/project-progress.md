# Aegis 项目进度（更新于 2026-04-05）

## 当前总体状态

- 已完成：`v1.0.0` 正式版主体范围（认证、巡检、自检、报表、管理看板、资产管理、审计、工具箱与审批流基础能力）
- 当前重点：从“可演示 / 可局部联调”推进到“稳定、可持续迭代的开发基线”
- 当前开发路线：`docs/phase1-development-plan.md`

## 本次新增进展（2026-04-05）

### 1) 本地启动与默认登录能力修复

已修复后端启动时未自动 seed 的问题：
- 恢复最小种子数据初始化
- 本地启动后会自动补齐默认管理员与示例数据

新增 / 调整：
- `backend/app/main.py`
- `backend/.env.example`
- `.gitignore`
- `docs/integration-quickstart.md`

结果：
- 本地可直接启动并使用默认管理员登录
- 默认管理员：`admin / local_admin_pass_2026`

### 2) 第一阶段 A：测试护栏与 smoke 增强

已新增并跑通后端回归测试：
- `backend/tests/test_auth_basic.py`
- `backend/tests/test_auth_profile.py`
- `backend/tests/test_inspections.py`
- `backend/tests/test_selfchecks.py`
- `backend/tests/test_toolbox.py`
- `backend/tests/test_ai.py`
- `backend/tests/test_admin_assets.py`
- `backend/tests/test_admin_systems.py`
- `backend/tests/test_audit_logs.py`

测试覆盖：
- auth
- inspections
- selfchecks
- toolbox
- ai
- admin / assets / audit

本地验证结果：
- `pytest -q` → `18 passed`

脚本增强：
- 新增 `scripts/dev-check.sh`
- 增强 `scripts/iteration3_smoke.sh`

当前 smoke 已覆盖：
1. `healthz`
2. 登录
3. `/auth/me`
4. 创建系统
5. 创建自检模板
6. 提交简化自检
7. 创建并审批工具任务
8. AI 诊断
9. 创建资产并查询 summary
10. 查询审计日志

### 3) 第一阶段 B：本地开发体验整理（进行中）

已新增 / 整理脚本：
- `scripts/dev-up.sh`
- `scripts/dev-stop.sh`
- `scripts/dev-reset.sh`
- `scripts/dev-status.sh`
- `scripts/dev-check.sh`

目标：
- 新环境更容易启动
- 常见排障更容易定位
- 降低接手成本

## 历史进展（保留）

### 达梦接入与验收增强

已支持两种达梦配置方式：
- 方式A：`DATABASE_URL` 完整连接串
- 方式B：`DM_HOST/DM_PORT/DM_NAME/DM_USER/DM_PASSWORD` 拆分配置（优先级更高）

涉及文件：
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/alembic/env.py`
- `backend/dameng.env.example`
- `docs/dameng-setup.md`

### 达梦检查脚本

新增脚本：`scripts/check_dm_connection.sh`

脚本会自动执行：
1. 达梦端口连通检查（127.0.0.1:5236）
2. Alembic 迁移（`alembic upgrade head`）
3. 后端启动
4. `/healthz` 健康检查
5. 登录检查（`/api/v1/auth/login`）
6. profile / change-password 写库回归

### 离线 AI（Ollama）接入

已将离线模型接入以下接口，并保留规则引擎回退：
- `POST /api/v1/ai/diagnose`
- `POST /api/v1/ai/offline/analyze`

新增 / 更新文件：
- `backend/app/services/offline_llm.py`
- `backend/app/api/ai.py`
- `backend/app/core/config.py`
- `backend/dameng.env.example`
- `docs/offline-ai-setup.md`
- `scripts/setup_offline_ai.sh`

## 下一步建议

### 第一优先级
- 继续完成第一阶段 B 的文档与脚本收拢
- 验证 `dev-up / stop / reset / status` 在干净环境中的可用性

### 第二优先级
- 开始第一阶段 C：工具箱 / 审批流闭环第一步
- 统一任务状态与结果结构

### 第三优先级
- 开始第一阶段 D：管理后台轻量模块化
