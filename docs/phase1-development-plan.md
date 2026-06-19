# Aegis 第一阶段开发计划

> 更新时间：2026-04-05
> 目标：把项目从“可演示 / 可局部联调”推进到“稳定、可持续迭代、可快速接手开发”的基线状态。

---

## 1. 阶段目标

第一阶段不追求一次性增加大量新功能，重点做四件事：

1. **补关键回归测试**：给现有主链路加护栏，避免后续开发反复改坏。
2. **整理本地开发体验**：让新环境/新同事能够更快跑起来并定位问题。
3. **补强工具箱 / 审批流主链路**：把现有“半 mock 半真实”能力整理成可持续演进的闭环。
4. **做管理后台轻量模块化**：降低 `frontend-admin/app.js` 的复杂度，为后续扩展打基础。

---

## 2. 范围与不做事项

### 2.1 本阶段纳入范围

- 后端关键接口测试与 smoke 脚本增强
- 本地开发脚本与文档整理
- 工具任务状态流转补强
- 管理后台最小粒度模块拆分（只做第一步，不做大重构）

### 2.2 本阶段暂不做

- 大规模 UI 重设计
- 前后端技术栈重构（如切换 React/Vue）
- 工具箱直接接入高风险真实执行器（如直接重启真实服务）
- 数据库专项深度优化（保留到后续阶段）

---

## 3. 迭代包 A：关键回归测试 + Smoke 护栏

### 3.1 目标

把现有最核心的功能链路纳入测试范围，保证后续功能开发不会轻易破坏已有能力。

### 3.2 任务拆分

#### A-1. 建立测试基础设施

**涉及文件：**
- `backend/tests/conftest.py`
- `backend/tests/` 目录下新增测试文件

**要做的事：**
- 统一测试环境变量（`SECRET_KEY`、`INIT_ADMIN_PASSWORD` 等）
- 建立可重复初始化的测试数据库
- 提供 `client` / `db_session` / `admin_token` 等 fixture
- 明确测试是否走 SQLite 内存库或临时文件库

**验收标准：**
- 本地执行 `pytest` 能稳定启动测试环境
- 单个测试与整套测试结果一致，不互相污染

#### A-2. 补 auth 相关测试

**建议新增文件：**
- `backend/tests/test_auth_profile.py`
- 调整 `backend/tests/test_auth_basic.py`

**覆盖接口：**
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `PUT /api/v1/auth/profile`
- `POST /api/v1/auth/change-password`

**重点验证：**
- 正确用户名密码可登录
- 错误密码登录失败
- 登录后获取用户资料成功
- 修改昵称/头像成功
- 修改密码后新密码生效、旧密码失效

#### A-3. 补巡检链路测试

**建议新增文件：**
- `backend/tests/test_inspections.py`

**覆盖接口：**
- `GET /api/v1/inspections/points/resolve`
- `POST /api/v1/inspections/records`
- `GET /api/v1/inspections/records`

**重点验证：**
- 纯数字二维码按 `system_id` 解析成功
- 旧版 `qr_content` 逻辑仍可解析
- 找不到巡检点时返回正确错误
- 巡检记录可创建、可查询

#### A-4. 补自检链路测试

**建议新增文件：**
- `backend/tests/test_selfchecks.py`

**覆盖接口：**
- `POST /api/v1/selfchecks/templates`
- `GET /api/v1/selfchecks/templates`
- `POST /api/v1/selfchecks/records`
- `POST /api/v1/selfchecks/records/simple`
- `GET /api/v1/selfchecks/records`

**重点验证：**
- 模板创建成功
- `records/simple` 在无模板时自动创建默认模板
- 模板与系统不匹配时能正确报错
- 自检记录列表返回正确

#### A-5. 补工具箱测试

**建议新增文件：**
- `backend/tests/test_toolbox.py`

**覆盖接口：**
- `POST /api/v1/toolbox/ping`
- `POST /api/v1/toolbox/port-check`
- `GET /api/v1/toolbox/error-logs`
- `POST /api/v1/toolbox/restart-task`
- `GET /api/v1/toolbox/tasks`
- `PUT /api/v1/toolbox/tasks/{task_id}/status`

**重点验证：**
- ping / port-check 基本成功路径
- restart task 创建成功
- 合法状态流转成功
- 非法状态流转失败
- 权限控制正确（如仅 super_admin 可改状态）

#### A-6. 补 AI 与后台管理测试

**建议新增文件：**
- `backend/tests/test_ai.py`
- `backend/tests/test_admin_assets.py`
- `backend/tests/test_admin_systems.py`
- `backend/tests/test_audit_logs.py`

**覆盖接口：**
- `POST /api/v1/ai/diagnose`
- `POST /api/v1/ai/offline/analyze`
- `GET /api/v1/ai/diagnoses`
- `POST /api/v1/admin/assets`
- `POST /api/v1/admin/assets/batch`
- `GET /api/v1/admin/assets`
- `GET /api/v1/admin/assets/export`
- `GET /api/v1/admin/assets/summary`
- `POST /api/v1/admin/systems`
- `GET /api/v1/admin/systems`
- `GET /api/v1/admin/audit-logs`

#### A-7. 增强 Smoke 脚本

**涉及文件：**
- `scripts/iteration3_smoke.sh`
- 新增 `scripts/dev-check.sh`

**建议流程：**
1. `healthz`
2. `login`
3. `/auth/me`
4. 创建系统
5. 创建模板
6. 提交简化自检
7. 创建 restart task
8. 审批 task
9. AI diagnose
10. 资产创建与 summary 校验

**验收标准：**
- 一条脚本能够清晰告诉开发者哪一步失败
- 输出结构化、便于 CI 接入

---

## 4. 迭代包 B：本地开发体验整理

### 4.1 目标

让项目在新环境中更容易启动、关闭、重置和排障。

### 4.2 任务拆分

#### B-1. 整理开发脚本

**涉及文件：**
- `scripts/dev-up.sh`
- 新增 `scripts/dev-stop.sh`
- 新增 `scripts/dev-reset.sh`
- 新增 `scripts/dev-status.sh`

**建议职责：**

##### `dev-up.sh`
- 检查 `.env` 是否存在，不存在则从 `.env.example` 复制
- 跑 Alembic 迁移
- 启动后端和两个前端
- 打印访问地址和日志路径

##### `dev-stop.sh`
- 停止 8000 / 5173 / 5174 对应本地进程

##### `dev-reset.sh`
- 停止服务
- 清理 SQLite 数据库与临时日志
- 重新迁移并启动

##### `dev-status.sh`
- 检查端口监听情况
- 检查 `/healthz`
- 输出日志文件位置

#### B-2. 统一文档入口与说明

**涉及文件：**
- `README.md`
- `backend/README.md`
- `docs/integration-quickstart.md`
- `docs/AGENT_CONTEXT.md`
- `docs/project-progress.md`
- `docs/DOCS_INDEX.md`

**要补充的内容：**
- 最小启动步骤
- 默认 seed 行为说明
- Python 环境注意事项
- 本地联调推荐顺序
- 当前前端技术形态（静态页面）
- AI / MySQL 作为可选增强，不应阻塞本地联调

**验收标准：**
- 新同事按文档可在 30 分钟内完成本地启动
- 常见排障入口清晰可见

---

## 5. 迭代包 C：工具箱 / 审批流闭环第一步

### 5.1 目标

把现有工具任务从“可创建、可审批”推进到“状态流转更完整、结果结构更统一”。

### 5.2 任务拆分

#### C-1. 扩展任务状态机

> 进度：进行中（已完成状态机、执行元数据、统一 result 结构与前端第一轮适配）

**涉及文件：**
- `backend/app/api/toolbox.py`
- `backend/app/models/tool_task.py`
- `backend/app/schemas/toolbox.py`
- 如需字段变化，新增 Alembic migration

**建议状态：**
- `pending_approval`
- `approved`
- `running`
- `done`
- `failed`
- `rejected`
- `cancelled`

**第一阶段策略：**
- 暂不接高风险真实执行器
- 先保证状态机、权限、审计、前端展示完整

#### C-2. 统一任务结果结构

**涉及文件：**
- `backend/app/api/toolbox.py`
- `backend/app/models/tool_task.py`
- `frontend-admin/app.js`
- `frontend-mobile/app.js`

**建议结果结构：**
```json
{
  "reason": "restart service",
  "note": "approved by admin",
  "executor": "system/mock/manual",
  "started_at": "2026-04-05T10:00:00Z",
  "finished_at": "2026-04-05T10:00:03Z",
  "success": true,
  "error": null
}
```

#### C-3. 结构化错误日志返回

**涉及文件：**
- `backend/app/api/toolbox.py`
- `backend/app/schemas/toolbox.py`
- `frontend-mobile/app.js`

**建议新增字段：**
- `source`
- `excerpt`
- `line_count`
- `truncated`
- `matched_keywords`

**价值：**
- 便于前端展示
- 便于 AI 分析复用
- 便于后续接统计/告警

---

## 6. 迭代包 D：管理后台轻量模块化第一步

### 6.1 目标

不做激进重构，先把 `frontend-admin/app.js` 中最通用、最容易膨胀的部分抽出来。

### 6.2 任务拆分

#### D-1. 抽公共 API / Auth / Utils

**建议新增文件：**
- `frontend-admin/js/api.js`
- `frontend-admin/js/auth.js`
- `frontend-admin/js/utils.js`
- `frontend-admin/js/dashboard.js`
- `frontend-admin/js/assets.js`
- `frontend-admin/js/toolbox.js`

**`app.js` 保留职责：**
- 页面初始化
- 模块装配
- 少量入口级事件绑定

#### D-2. 第一批迁移模块

**优先迁出的逻辑：**
1. `request()` / `headers()` / token / relogin
2. dashboard 自动刷新与数据渲染
3. 资产创建 / 查询 / 导出
4. toolbox 任务查询与状态更新

#### D-3. 增加开发者调试区（低成本高收益）

**涉及文件：**
- `frontend-admin/index.html`
- `frontend-admin/app.js` 或拆分后的模块

**建议展示：**
- 当前 API base
- token 状态
- 当前用户信息
- 最近一次请求时间
- `healthz` 快捷检测

---

## 7. 推荐执行顺序

### 第一顺位
**迭代包 A：关键回归测试 + Smoke 护栏**

原因：后续所有功能开发都要依赖这套护栏，否则每次改动都容易引入回归问题。

### 第二顺位
**迭代包 B：本地开发体验整理**

原因：能显著降低联调与接手成本，提高后续开发效率。

### 第三顺位
**迭代包 C：工具箱 / 审批流闭环第一步**

原因：这是最像“下一阶段产品能力”的增强点，也能直接提升系统完成度。

### 第四顺位
**迭代包 D：管理后台轻量模块化第一步**

原因：越早拆边界，后面继续堆功能时越不容易失控。

---

## 8. 建议验收口径

阶段完成后，至少满足以下条件：

1. 本地可通过文档 + 脚本完成启动与登录
2. 关键接口具备自动化测试覆盖
3. smoke 脚本能覆盖主链路
4. 工具任务具备更完整的状态流转
5. 管理后台已经抽出第一批公共模块，不再把所有逻辑堆在单文件中

---

## 9. 2026-05-08 补充：AI 阶段1/阶段2第一版已落地

本计划最初聚焦“开发基线”，但截至 2026-05-08，Aegis AI 相关能力已经额外完成一轮重要推进：

### 已额外完成
- OpenClaw 真实 provider 接入，替换 skeleton/mock 链路
- LAN / Tailscale / HTTPS 联调打通
- 移动端 AI 问答阶段1体验增强完成
- 阶段2第一版“附件先上传，再用 file_id 引用”的链路落地

### 当前关于 AI 会话的最终产品结论
- 应保留**同一次打开应用期间**的连续对话能力
- 不保留**本次打开之前**的历史聊天
- 重新打开应用后默认从空白新会话开始

### 如果下次继续开发 Aegis，建议优先顺序改为
1. 先回看 `docs/project-progress.md` 中 2026-05-08 的 AI 阶段进展
2. 优先补阶段2后续：
   - 更正式的文件上传 / 文件管理架构
   - 真机联调验证
   - 性能与响应时延优化
3. 再回到本计划中的回归测试 / smoke 护栏补强
4. 最后继续工具箱与管理后台的原路线

## 10. 对下一次会话的建议

若下次继续开发，建议优先按以下顺序推进：

1. 先看 `docs/project-progress.md` 最新进展
2. 若继续 AI 方向，先从阶段2后续与真机联调开始
3. 若回到基线治理，再做 **迭代包 A（回归测试）**
4. 再做 **迭代包 B（开发体验）**
5. 然后做 **迭代包 C（工具箱闭环）**
6. 最后做 **迭代包 D（前端轻模块化）**

如果用户只给一句“继续做 Aegis”，默认先查看上次 AI 阶段进度，再决定是继续阶段2还是回到测试护栏工作。
