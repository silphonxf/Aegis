# Aegis 持久化上下文（给我下次快速接入）

> 最后更新：2026-03-09  
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
- 近阶段重点：从“可演示/可局部联调”推进到“稳定、可持续迭代的开发基线”
- 第一阶段开发计划：`docs/phase1-development-plan.md`
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

4. Git 协作规则已变更：
   - 新功能必须在功能分支开发
   - 不直接提交到 `main`
   - 由用户手动 merge 回主分支

## 4. 关键文件地图（下次优先看）

### 业务总览
- `README.md`
- `docs/DOCS_INDEX.md`
- `docs/project-progress.md`

### 达梦接入
- `docs/dameng-setup.md`
- `backend/dameng.env.example`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/alembic/env.py`
- `scripts/check_dm_connection.sh`

### 验收与联调
- `docs/integration-quickstart.md`
- `docs/offline-ai-setup.md`
- `docs/login-common-pitfalls.md`

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
- [x] 登录常见误区文档补充（应用账号 vs 数据库账号）
- [x] 启动自动 seed 最小数据，恢复本地默认登录能力
- [x] 补充 `backend/.env.example`
- [ ] 按 `docs/phase1-development-plan.md` 推进第一阶段开发
- [ ] 关键写库接口补充达梦集成测试
- [x] 补关键接口回归测试与 smoke 增强
- [x] 整理本地开发脚本（up/stop/reset/status）
- [ ] 完成第一阶段 C：工具箱 / 审批流闭环剩余交互与展示优化

## 7. 最近更新记录（倒序）

### 2026-04-05
- 新增 `docs/phase1-development-plan.md`，明确第一阶段开发路线：测试护栏、本地开发体验、工具箱闭环、后台轻模块化
- `docs/DOCS_INDEX.md` 增加第一阶段开发计划入口
- `docs/AGENT_CONTEXT.md` 同步当前阶段目标与待办
- 修复后端启动自动 seed，恢复本地默认管理员登录能力
- 补充 `backend/.env.example`，并修复 `.gitignore` 对示例环境文件的误伤
- 新增 `CONTRIBUTING.md`，明确后续功能统一走功能分支，由用户手动 merge 到 `main`
- 第一阶段 A（测试护栏）已完成并跑通 `18 passed`
- 第一阶段 B（本地开发体验整理）已完成，新增 `dev-up / stop / reset / status`
- 第一阶段 C 已开始，当前分支：`feat/toolbox-task-workflow`
- 第一阶段 D 已开始，当前分支：`feat/admin-light-modularization`

### 2026-03-09
- 文档治理：清理阶段性重复/里程碑快照文档，新增统一入口 `docs/DOCS_INDEX.md`
- README 与 AGENT_CONTEXT 的文档链接统一收敛到长期维护文档
- 清理分支：`chore/docs-prune-milestones`

### 2026-03-09（功能接续）
- 接续开发：离线 AI（Ollama）正式接入 `diagnose` 与 `offline/analyze` 主链路
- 新增文件：`backend/app/services/offline_llm.py`、`docs/offline-ai-setup.md`、`scripts/setup_offline_ai.sh`
- 配置扩展：新增 `OFFLINE_AI_*` 参数（enabled/provider/model/base_url/timeout）
- 稳健性补强：provider 大小写无关、LLM 空建议判错并自动回退规则引擎
- 达梦验收增强：`scripts/check_dm_connection.sh` 新增写库接口检查（profile/change-password）并带密码回滚
- 文档补充：新增 `docs/login-common-pitfalls.md`，明确应用账号与数据库账号区别
- 观测性增强：达梦检查脚本支持输出 JSON 报告（成功/失败均可落盘）
- API观测性增强：`/ai/diagnose` 与 `/ai/offline/analyze` 返回并记录 `elapsed_ms`、`fallback_reason`
- 当前分支：`feat/dameng-integration`（持续新增提交，待 push）

### 2026-03-06
- 新增AI离线错误日志分析MVP：规则引擎+任务结果表+离线分析API
- 同步时间：2026-03-06 18:00:22 +0800
- 新增局域网HTTPS启动脚本，支持相机/NFC调试（前后端均HTTPS）
- 同步时间：2026-03-06 15:31:51 +0800
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
