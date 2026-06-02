# Aegis 项目进度（更新于 2026-05-11）

## 当前总体状态

- 已完成：`v1.0.0` 正式版主体范围（认证、巡检、自检、报表、管理看板、资产管理、审计、工具箱与审批流基础能力）
- 当前重点：Aegis AI 能力已从 skeleton/mock 联调推进到真实 OpenClaw 接入，并完成阶段2第一版附件引用式链路与移动端 AI 体验收尾
- 当前开发路线：`docs/phase1-development-plan.md`


## 本次新增进展（2026-06-02）

### 0) 共享主数据第一优先级缺口补齐

已完成：
- 巡检点 `system_id` 调整为可空，支持“只绑定机房/区域”的共享点位模型
- 新增迁移：`backend/alembic/versions/20260602_17_shared_point_system_nullable.py`
- 管理端资产列表与 CSV 导出补齐共享字段：
  - `room_id`
  - `ip_address`
  - `port`
  - `connection_type`
  - `remark`
  - `updated_at`
- 管理端机房列表补齐分页、`total` 与 `is_active` 过滤语义
- 管理端巡检点创建补齐校验：
  - 机房必须存在且启用
  - 传入系统时系统必须存在
  - 不再把缺省 `system_id` 硬编码为 `1`
- 管理端新增资产弹窗中，系统与机房字段从手输 ID 收敛为共享主数据下拉
- 新增/补强回归测试：
  - 机房列表分页与启用状态返回
  - 只绑定机房的巡检点创建
  - 缺失机房的巡检点创建拒绝
  - 资产共享字段列表返回与 CSV 导出

验证结果：
- `./.venv/bin/pytest backend/tests/test_rooms_points.py backend/tests/test_admin_assets.py -q` → `7 passed`
- `./.venv/bin/pytest backend/tests/test_rooms_points.py backend/tests/test_admin_assets.py backend/tests/test_admin_systems.py backend/tests/test_inspections.py -q` → `11 passed`

当前剩余：
- 继续把系统负责人、机房、点位、资产的管理端页面做成完整 CRUD，而不是只提供创建/列表
- 后续将 `emergency_hosts` / `runbooks` 与系统、机房、资产下拉做正式联动

## 本次新增进展（2026-05-14）

### 0) 应急处置移动端前端骨架与管理端配置方案初稿

已完成：
- 工作台“辅助工具”新增 `应急处置` 入口
- 移动端新增应急处置页面，按 3 个模块拆分：
  - 服务器操作
  - 数据库操作
  - 进程操作
- 服务器操作前端已按确认口径收紧为：
  - 主机名
  - IP
  - 重启按钮
- 进程操作前端已按确认口径收紧为：
  - 进程名
  - 进程 ID
  - 重启按钮
  - 关闭按钮
- 数据库操作已补齐以下前端入口：
  - FOC 密码查询
  - FOC 死锁处理
  - FOC 数据库闪回
  - 数据库表空间
- FOC 密码查询已实现 3×3 前端表单：
  - 系统下拉
  - 工号输入
  - 查询按钮
- 当前查询结果先按产品确认使用简单文本弹窗，不做复杂结果卡片

已输出设计文档：
- `docs/emergency-ops-admin-design.md`

设计初步结论：
- 后端后续通过管理端单独菜单维护应急处置配置
- 配置应按以下维度拆分：
  - SSH 主机配置
  - 服务器动作配置
  - 数据库动作配置
  - 进程动作配置
- 需重点注意敏感信息加密：
  - SSH 密码
  - SSH 私钥
  - 私钥口令
- 主密钥应来自环境变量，不进入代码仓库

## 本次新增进展（2026-05-11）

### 0) 移动端新版 UI 骨架重构与联调前核查

已完成：
- 移动端 `frontend-mobile/index.html` 已重构为新版信息架构：
  - 底部 4 Tab：`工作台 / 巡检 / 自检 / 我的`
  - 工作台承载“今日待办 / 快捷操作 / 辅助工具 / 最近动态`
  - `我的` 收敛为账号相关，不再承载 Ping / 抓包 / AI 问答 / 工具任务
- 二级功能已改为全屏 detail page：
  - 巡检：扫码巡检 / NFC 巡检 / 巡检记录
  - 自检：系统状态 / 提交自检 / 错误日志分析
  - 工作台工具：AI 问答 / Ping / 抓包分析 / 工具任务
- `frontend-mobile/style.css` 已按新版结构重排，支持：
  - bottom tabs
  - tab-screen / detail-screen
  - detail-topbar
  - 工作台卡片 / 列表 / AI 聊天区
- `frontend-mobile/app.js` 已完成新版导航主线切换：
  - 底部 Tab 切换
  - detail page 打开 / 返回
  - 顶部标题跟随一级页 / 功能页变化
  - 当前一级 Tab 通过 `sessionStorage` 记忆
- 旧移动端导航兼容层已清理：
  - 旧 `panel/subpage` 结构已从 HTML 中移除
  - 旧 `switchPanel()` / `showSub()` 已从服务版本脚本中移除
- UI 命名进一步收口：
  - `btnLogoutInUserCenter` → `btnLogout`
  - `btnAppRestart` → `btnCreateToolTask`
  - `appToolResult` → `toolTaskResult`

已完成的联调前核查：
- 已确认服务输出的 `index.html` / `app.js` 确实是新版，不是工作区与服务版本不一致
- 已确认以下高频功能在新版 HTML / JS 中的关键 DOM 与绑定字段对位正常：
  - AI 问答
  - Ping
  - 抓包分析
  - 工具任务
  - 系统状态
  - 扫码巡检 / NFC
- 已确认以下前端 → 后端接口链路在代码层对位正常：
  - `POST /api/v1/ai/chat/v2`
  - `POST /api/v1/toolbox/ping`
  - `POST /api/v1/toolbox/capture/analyze`
  - `GET /api/v1/toolbox/tasks`
  - `POST /api/v1/toolbox/restart-task`
  - `GET /api/v1/monitoring/overview`
  - `POST /api/v1/inspections/records`

当前已知风险收敛为：
- 真机移动端仍可能受 **HTTPS 前端 + HTTP 后端** 的 mixed-content / fetch 限制影响
- 高频功能的真实失败原因后续要区分：
  - UI 问题
  - 权限不足（多个接口要求 `admin` / `super_admin`，巡检提交要求 `inspector` / `admin` / `super_admin`）
  - 浏览器能力限制（相机 / NFC / secure context）
  - 真机网络与协议问题

### 1) OpenClaw 真实接入替换 skeleton 适配链路

### 1) OpenClaw 真实接入替换 skeleton 适配链路

已完成：
- Aegis 后端 AI provider 从本地 skeleton/mock 适配层切换到真实 OpenClaw gateway
- 默认本机联调地址为：`http://127.0.0.1:18789`
- 已确认 `/v1/responses` 真实可用
- `POST /api/v1/ai/chat` 与 `POST /api/v1/ai/diagnose` 已可真实走 OpenClaw

涉及文件：
- `backend/app/services/openclaw_client.py`
- `backend/app/services/ai_provider.py`
- `backend/app/core/config.py`
- `backend/.env`
- `backend/.env.example`

### 2) 局域网 / Tailscale / HTTPS 联调能力补齐

已完成：
- 启动局域网 HTTPS 访问：5173 / 5174 / 8000
- 修复移动端与 Tailscale 下的 CORS 问题
- 当前可通过 LAN / Tailscale 继续做移动端真机联调

关键结论：
- 之前 `Failed to fetch` 的核心原因是 CORS，而不是 AI 接口本身不可用

### 3) 移动端 AI 问答阶段1体验增强完成

已完成：
- 聊天气泡高度修复
- 发送后清空输入框
- `Enter` 发送 / `Shift+Enter` 换行
- AI 占位气泡
- 失败重试
- 按钮 loading 与防重复提交
- 附件数限制（最多 4 个）
- 附件大小限制（2MB）
- 图片上传前压缩
- 错误日志 AI 分析 loading / 禁用 / 精简结果展示
- 会话顶部状态提示
- “新会话”与“清空会话”分离

涉及文件：
- `frontend-mobile/index.html`
- `frontend-mobile/style.css`
- `frontend-mobile/app.js`

### 4) AI 阶段2第一版：附件引用式链路落地

已完成：
- 新增附件上传接口：`POST /api/v1/ai/files/upload`
- 新增引用式聊天接口：`POST /api/v1/ai/chat/v2`
- 附件不再直接作为 base64 塞入聊天接口
- 后端保存附件并返回 `file_id`
- 聊天接口改为传 `file_id + name + type + size`
- 文本附件支持轻量 `extracted_text` 提取后参与 prompt

新增模型 / 迁移：
- `backend/app/models/ai_chat_file.py`
- `backend/app/models/ai_chat_message.py`
- `backend/app/models/ai_chat_summary.py`
- `backend/alembic/versions/20260508_11_ai_chat_files.py`
- `backend/alembic/versions/20260508_12_ai_chat_messages.py`
- `backend/alembic/versions/20260508_13_ai_chat_summaries.py`

新增接口 / schema：
- `backend/app/api/ai_files.py`
- `backend/app/schemas/ai_chat_file.py`

### 5) 连续对话需求最终收敛结论

这轮中连续对话需求经历过几次收敛，最终确定为：
- **同一次打开应用期间**：允许连续对话
- **关闭应用 / 重新打开后**：默认空白新会话
- **不保留本次打开之前的聊天历史**

因此当前产品实现方向是：
- 前端 AI 聊天记录改为 `sessionStorage`
- 页面打开期间保留当前会话
- 关闭应用后自动清空
- 服务端仅按当前 `conversation_id` 回放最近几轮上下文，不做长期历史恢复

### 6) 当前已知现实问题

- OpenClaw 真实响应耗时仍偏高，联调时观察到约 `20~33s`
- 因此前端已增加分阶段提示：
  - 上传附件中
  - 整理上下文中
  - AI 回复中
- 服务端摘要型长期历史方案已尝试过，但当前不是最终方向，后续如需恢复，应优先做更轻的增量式方案

## 历史进展（保留）

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

### 3) 第一阶段 B：本地开发体验整理

已新增 / 整理脚本：
- `scripts/dev-up.sh`
- `scripts/dev-stop.sh`
- `scripts/dev-reset.sh`
- `scripts/dev-status.sh`
- `scripts/dev-check.sh`

结果：
- 新环境更容易启动
- 常见排障更容易定位
- 接手成本明显降低

### 4) 第一阶段 C：工具箱 / 审批流闭环（进行中）

> 当前功能分支：`feat/toolbox-task-workflow`

已完成第一步基础能力：
- 工具任务状态机扩展为：
  - `pending_approval`
  - `approved`
  - `running`
  - `done`
  - `failed`
  - `rejected`
  - `cancelled`
- `tool_tasks` 新增字段：
  - `executor`
  - `started_at`
  - `finished_at`
- 统一任务 `result` 结构，包含：
  - `reason`
  - `note`
  - `executor`
  - `started_at`
  - `finished_at`
  - `success`
  - `error`
- `/toolbox/error-logs` 返回新增结构化字段：
  - `excerpt`
  - `line_count`
  - `truncated`
  - `matched_keywords`
- 管理后台已适配新版任务状态显示
- 移动端已接入“创建重启任务 / 查看最近工具任务”

涉及文件：
- `backend/alembic/versions/20260405_10_tool_task_workflow.py`
- `backend/app/models/tool_task.py`
- `backend/app/schemas/toolbox.py`
- `backend/app/api/toolbox.py`
- `frontend-admin/index.html`
- `frontend-admin/app.js`
- `frontend-mobile/index.html`
- `frontend-mobile/app.js`

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

### 5) 第一阶段 D：管理后台轻量模块化（进行中）

> 当前功能分支：`feat/admin-light-modularization`

已完成第一轮拆分：
- `frontend-admin/js/api.js`
- `frontend-admin/js/auth.js`
- `frontend-admin/js/dashboard.js`
- `frontend-admin/js/toolbox.js`
- `frontend-admin/js/assets.js`
- `frontend-admin/js/users.js`
- `frontend-admin/js/systems.js`
- `frontend-admin/js/rules-audit.js`
- `frontend-admin/js/templates.js`

结果：
- `frontend-admin/app.js` 已缩减为入口/装配层
- 前端仍保持原有静态形态，无需引入新框架
- 后续继续增强时，复杂度会显著低于单文件模式

补充说明：
- 模块结构说明见：`frontend-admin/js/README.md`

## 当前补充进展（2026-05-27）

### 管理端 V2 重构主线重新定位完成

已重新扫描并对齐以下文档与实现：
- `docs/emergency-ops-admin-design.md`
- `docs/admin-console-v2-frontend-implementation.md`
- `frontend-admin/index.html`
- `backend/app/models/*`
- `backend/app/api/admin.py`
- `backend/app/api/inspections.py`
- `backend/app/api/systems.py`
- `frontend-mobile/app.js`

本次确认的重构原则：
- 管理端不是独立业务端，而是移动端的**配置界面 + 审阅界面**
- 系统 / 用户 / 机房 / 巡检点 / 应急处置目标数据必须是**两端共享主数据**
- 后续应急处置配置（SSH 主机 / 服务器动作 / 数据库动作 / 进程动作）本质上都是为了移动端应急处置入口服务
- 用户侧已进一步确认：`users` 不再补扩展字段，且现有 `nickname` 可移除；`systems` 按共享主数据目标方案改造，并立即引入系统-用户关联表

当前已识别出的实现差异：

1. **系统负责人模型仍偏单负责人**
- 当前 `systems.owner_user_id` 只能挂单人
- 与设计文档中的“系统负责人支持多选 / 多班次交接”不一致
- 后续应收敛为系统-用户多对多关系，而不是单个 owner 字段

2. **机房主数据尚未独立成表**
- 当前巡检点 `inspection_points` 仍以 `location` 字符串承载位置语义
- 资产 `assets.location` 也仍为字符串
- 这会导致机房、资产、巡检点、二维码/NFC 点位无法做强关联

3. **移动端已在真实消费共享数据，但管理端主数据还没完全收口**
- 移动端巡检当前依赖：`system_id`、`point_id`、二维码解析结果
- 管理端已经开始承接“机房巡检配置与记录”“基础数据录入”工作台
- 但后端层还缺真正的机房/点位/系统负责人共享主模型

4. **应急处置配置当前仍是独立 JSON 配置态**
- `app/services/emergency_config.py` 当前基于 `config/emergency_ops.json`
- 适合联调占位，但还不满足后续“按系统 / 主机 / 机房 / 角色 / 移动端入口”联动的正式形态

当前判断：
- 上一轮工作并不是停在纯前端视觉骨架
- 真正的下一步应转入：**共享主数据模型收敛 + 管理端承接移动端配置源重构**

建议的下一步落地顺序：

### 第一优先级：先收主数据模型
建议补齐或重构为以下共享实体：
- `users`
- `systems`
- `rooms`（机房/区域）
- `system_user_bindings`（系统-用户多对多，区分负责人/值班/审阅角色）
- `assets`
- `inspection_points`（绑定 `room_id`，必要时再挂 `system_id`）
- `emergency_hosts` / `runbooks` / `runbook_bindings`（后续替代当前 JSON 配置）

### 第二优先级：再改管理端承接页
围绕移动端配置源改造：
- 系统页：负责人多选、运行服务器、检查频次、关联预案
- 机房页：机房主数据、二维码/NFC 点位、巡检记录审阅
- 基础数据页：用户、服务器、资产统一为共享下拉源

### 第三优先级：最后把应急处置配置正式入库
目标是让管理端配置：
- SSH 主机
- 服务器动作
- 数据库动作
- 进程动作

再由移动端按场景消费：
- 主机名 / IP / 动作按钮 / 审批状态 / 执行结果

## 下一步建议

### 第一优先级
- 输出一版“现状表结构 → 目标共享表结构”的最小迁移方案
- 明确哪些字段保留兼容，哪些字段需要迁移/废弃

### 第二优先级
- 为管理端 / 移动端补共享主数据接口草案
- 优先覆盖：系统负责人、机房、巡检点、服务器基础数据

### 第三优先级
- 将当前 JSON 版应急处置配置设计为可迁移到数据库的正式模型
