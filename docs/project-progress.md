# Aegis 项目进度（更新于 2026-05-11）

## 当前总体状态

- 已完成：`v1.0.0` 正式版主体范围（认证、巡检、自检、报表、管理看板、资产管理、审计、工具箱与审批流基础能力）
- 当前重点：Aegis AI 能力已从 skeleton/mock 联调推进到真实 OpenClaw 接入，并完成阶段2第一版附件引用式链路与移动端 AI 体验收尾
- 当前开发路线：`docs/phase1-development-plan.md`

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

## 下一步建议

### 第一优先级
- 完成 D 分支的收尾整理与联调验证
- 将当前模块拆分成果推送并等待用户 review / merge

### 第二优先级
- 回到 C 分支继续完善工具任务交互细节（如需）

### 第三优先级
- 进入下一轮功能开发时，继续沿用功能分支工作流
