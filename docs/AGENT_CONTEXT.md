# Aegis 持久化上下文（给我下次快速接入）

> 最后更新：2026-06-04
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

5. Aegis 产品配置化原则：
   - 移动端是执行端和展示端，管理端是配置端和审阅端。
   - 移动端每一个业务功能的行为、数据范围、模板、skill、脚本、阈值、人员来源，都应优先通过管理端配置。
   - 后续新增或修改移动端功能时，不能把业务规则硬编码在移动端代码里；应先明确管理端需要新增哪些配置项、配置页面、后端字段和审计记录。
   - 如果用户只提出移动端改造需求，我需要主动提醒：该能力在管理端应如何配置、谁维护、移动端消费哪个接口。
   - 当前示例：系统自检的 AI 自检 `skill` 必须在管理端“系统”模块中配置，字段非必填；未配置时移动端显示“暂未配置ai自检项目”，不通过改代码补默认业务 skill。

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
- [x] 共享主数据第一优先级缺口补齐：机房、点位、资产共享字段与测试
- [x] 共享主数据 CRUD 第二步：系统、机房、巡检点、资产后端更新/停用接口，资产前端编辑/停用入口
- [x] 补关键接口回归测试与 smoke 增强
- [x] 整理本地开发脚本（up/stop/reset/status）
- [ ] 完成第一阶段 C：工具箱 / 审批流闭环剩余交互与展示优化

## 7. 最近更新记录（倒序）


### 2026-06-03（系统配置与移动端日志路径）
- 管理端“资产与日常运维”子菜单收敛为“系统 / 资产 / 用户”
- 系统页面第一版完成：列表、搜索、环境/状态筛选、排序、新增、编辑
- 系统新增/编辑支持 `host_address`、管理员 ID 列表与多条日志绝对路径
- 后端新增迁移 `20260603_18_system_host_logs.py`，新增 `systems.host_address` 与 `system_log_configs`
- 移动端系统可见性改为：`admin/super_admin` 看全部系统，普通用户只看自己绑定为管理员的系统
- 移动端错误日志分析页可按可见系统读取管理端配置的日志绝对路径
- 已跑通：`./.venv/bin/pytest backend/tests/test_admin_systems.py -q`（`4 passed`）
- 已跑通：前端 admin/mobile 关键 JS `node --check`
- 剩余：真实 SSH 远程日志读取需要继续补目标服务器 SSH 凭据绑定

### 2026-06-03（日志分析修复）
- 修复移动端错误日志分析读取失败
- 根因：移动端默认请求 `aegis-backend-https.log`，后端实际候选文件为 `.logs/backend-https.log` / `.logs/backend.log`
- 移动端默认文件名改为 `backend-https.log`
- 后端 `_read_selected_logs` 增加旧文件名别名兼容，避免浏览器旧选项继续触发 `LOG_FILE_NOT_FOUND`
- `scripts/dev-up.sh` 后端 HTTPS 日志输出改为 `.logs/backend-https.log`，`scripts/dev-status.sh` 同步展示该文件
- 已跑通：`./.venv/bin/pytest backend/tests/test_toolbox.py -q`（`6 passed`）
- 已实测 HTTPS 日志接口能读取 `backend-https.log`

### 2026-06-03（共享主数据 CRUD）
- 接续共享主数据管理端 CRUD 缺口
- 后端补齐系统、机房、巡检点、资产的更新/软停用接口
- 系统更新支持负责人绑定替换与清空；系统列表返回 `is_active`
- 资产创建、更新、批量导入统一校验系统/机房引用
- 管理端资产列表新增编辑/停用操作列，资产弹窗复用为新增/编辑两种模式
- 新增回归测试覆盖系统、机房、巡检点、资产的更新/停用与错误引用拒绝
- 已跑通：`./.venv/bin/pytest backend/tests/test_rooms_points.py backend/tests/test_admin_assets.py backend/tests/test_admin_systems.py -q`（`13 passed`）
- 已跑通：`node --check frontend-admin/js/assets.js && node --check frontend-admin/js/modals.js && node --check frontend-admin/app.js`

### 2026-06-02
- 接续 `docs/project-progress.md` 中“共享主数据模型收敛 + 管理端承接移动端配置源重构”的第一优先级
- 新增迁移 `20260602_17_shared_point_system_nullable.py`，允许巡检点不强制绑定系统，只绑定机房/区域
- 管理端资产列表与 CSV 导出补齐 `room_id/ip_address/port/connection_type/remark/updated_at` 等共享字段
- 管理端机房列表补齐分页、`total`、启用状态返回与默认只查启用数据
- 巡检点创建补齐 room/system 校验，移除缺省 `system_id=1` 硬编码
- 管理端资产创建弹窗将系统、机房从手输 ID 改为共享主数据下拉
- 已跑通：`./.venv/bin/pytest backend/tests/test_rooms_points.py backend/tests/test_admin_assets.py backend/tests/test_admin_systems.py backend/tests/test_inspections.py -q`（`11 passed`）

### 2026-05-14
- 接续确认当前工作分支：`feat/ai-session-restore-test`
- 已补齐抓包分析 AI 接口：`POST /api/v1/toolbox/capture/analyze`
- 新增 schema：`backend/app/schemas/capture.py`
- 放宽离线分析 `source_type`，支持 `capture_result`
- 新增回归测试：抓包分析接口、AI 会话重命名
- 已本地跑通：`./.venv/bin/pytest backend/tests/test_toolbox.py backend/tests/test_ai_conversations.py -q`（`6 passed`）
- 本地开发脚本已切到 `.venv + HTTPS static server` 模式，便于真机/LAN 联调

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
