# Aegis 脚本清单

> 更新时间：2026-06-10

本清单用于后续清理 `scripts/` 目录。当前先保留脚本行为，只记录用途、使用场景和清理建议。

## 本地开发启动

| 脚本 | 作用 | 建议 |
|---|---|---|
| `dev-up.sh` | 推荐的本地开发启动脚本。生成/复用本地 HTTPS 证书，执行迁移，启动 HTTPS 后端、移动端和管理端，并输出本机/LAN 访问地址。 | 保留，作为本地开发主入口。 |
| `dev-stop.sh` | 停止本地开发的后端、移动端和管理端进程。 | 保留，与 `dev-up.sh` 配套。 |
| `dev-status.sh` | 查看 8000/5173/5174 端口监听、后端健康检查和日志位置。 | 保留，与 `dev-up.sh` 配套。 |
| `dev-reset.sh` | 停止服务，删除本地 SQLite 数据库和日志，然后重新执行 `dev-up.sh`。 | 保留，但应仅用于本地环境。 |
| `dev-check.sh` | 对指定后端执行基础检查：`/healthz`、登录、`/auth/me`。需要显式传入密码。 | 保留，可作为轻量 smoke。 |
| `serve_https.py` | 用 Python 内置 HTTP server 以 HTTPS 方式服务静态目录，供移动端/管理端本地联调使用。 | 保留，被 `dev-up.sh`、`server-up.sh`、`start_lan_https.sh` 依赖。 |

## 服务器或 LAN 启动

| 脚本 | 作用 | 建议 |
|---|---|---|
| `server-up.sh` | 面向服务器的 HTTPS 启动脚本。要求 `backend/.env` 已配置安全值，会拒绝弱默认密码/占位配置，执行迁移后启动三端服务。 | 保留，后续可补配套 `server-status.sh` / `server-stop.sh`。 |
| `start_lan_https.sh` | 早期 LAN HTTPS 启动脚本，固定使用端口 8000/5173/5174，生成开发证书并启动三端。 | 候选删除或并入 `dev-up.sh`，功能与 `dev-up.sh` 重叠。 |

## 验收与检查

| 脚本 | 作用 | 建议 |
|---|---|---|
| `iteration3_smoke.sh` | 端到端冒烟：健康检查、登录、创建系统、自检模板、自检记录、重启审批、AI 诊断、资产、审计日志。 | 保留或改名为通用 smoke；当前名称带历史迭代色彩。 |
| `ai_perf_check.py` | 登录本地 HTTPS 后端，创建 AI 会话并调用 `/api/v1/ai/chat/v2`，输出耗时和回复信息。 | 保留，后续可参数化账号、密码和 Base URL。 |

## AI 与上下文

| 脚本 | 作用 | 建议 |
|---|---|---|
| `setup_offline_ai.sh` | 启动 Ollama、拉取指定模型，并输出 Aegis 离线 AI `.env` 推荐配置。 | 保留，后续可补网络/磁盘空间预检查。 |
| `sync_agent_context.sh` | 更新 `docs/AGENT_CONTEXT.md` 最近记录，提交并推送当前分支。 | 谨慎保留：会自动提交和推送，适合人工明确触发，不适合被其他脚本隐式调用。 |

## 当前清理建议

1. 优先保留 `dev-up.sh`、`dev-stop.sh`、`dev-status.sh`、`dev-reset.sh`、`serve_https.py` 作为本地开发主链路。
2. 将 `start_lan_https.sh` 标记为可删除候选，因为它与 `dev-up.sh` 功能重复且端口/日志命名更旧。
3. 将 `iteration3_smoke.sh` 重命名为更长期的 `smoke.sh`，避免后续误以为只服务第三轮迭代。
4. 为 `ai_perf_check.py` 增加命令行参数，避免账号、密码、Base URL 写死。
