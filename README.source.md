# 运维助手（Aegis）

运维助手是一个面向移动端的一体化运维应用，覆盖机房巡检、系统自查、报表分析、后台管理与全局监控。

## 核心目标
- 巡检数字化：扫码 / NFC 快速登记
- 自查标准化：日检 / 周检 / 年检可配置模板
- 数据可视化：巡检与自检报表、趋势分析
- 管理闭环：移动端执行 + 管理后台监管 + 超级管理员总览
- 平台兼容：Python 技术栈 + SQLite/MySQL 数据库 + Docker 部署

## 仓库结构
- `docs/`：产品文档、开发计划、进度与接手说明
- `backend/`：Python 后端（API、业务逻辑、数据层）
- `frontend-mobile/`：移动端前端（H5/PWA）
- `frontend-admin/`：后台管理前端
- `deploy/`：容器化与部署配置
- `scripts/`：开发与运维脚本

## 当前状态
- `v1.0.0` 主体功能已完成
- 已补本地默认 seed（角色 / admin / 示例系统 / 巡检点）
- 已补第一阶段回归测试与 smoke 护栏
- 当前推荐继续推进：`docs/phase1-development-plan.md`

## 本地快速启动（推荐）

### 一键启动
```bash
cd /home/xf/.openclaw/workspace/projects/Aegis
./scripts/dev-up.sh
```

### 一键检查
```bash
./scripts/dev-check.sh http://127.0.0.1:8000 admin local_admin_pass_2026
```

### 一键冒烟
```bash
./scripts/iteration3_smoke.sh http://127.0.0.1:8000 admin local_admin_pass_2026
```

### 停止服务
```bash
./scripts/dev-stop.sh
```

### 重置本地环境
```bash
./scripts/dev-reset.sh
```

### 查看状态
```bash
./scripts/dev-status.sh
```

## 本地默认地址
- 管理后台：`http://127.0.0.1:5174`
- 移动端：`http://127.0.0.1:5173`
- 后端 API：`http://127.0.0.1:8000`

## 本地默认账号
- 用户名：`admin`
- 密码：`local_admin_pass_2026`

> 若你已有自定义 `backend/.env`，以你的本地配置为准。

## 推荐阅读顺序
- `docs/DOCS_INDEX.md`：文档入口
- `docs/phase1-development-plan.md`：第一阶段开发计划
- `docs/integration-quickstart.md`：联调与启动说明
- `docs/project-progress.md`：项目进展
- `docs/AGENT_CONTEXT.md`：持续上下文与接手要点
- `CONTRIBUTING.md`：协作与分支开发规则

## 说明
- 本地联调默认走 SQLite，可按需切换 MySQL。
- 离线 AI（Ollama）接入见：`docs/offline-ai-setup.md`
