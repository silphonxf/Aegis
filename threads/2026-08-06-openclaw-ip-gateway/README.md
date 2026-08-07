# 2026-08-06 OpenClaw IP 工具网关进度

## 目标

把 Aegis 的 IP 研判和山石封禁能力作为远程工具网关提供给另一台服务器的
OpenClaw，并由飞书 `open_id` 白名单控制查询和封禁权限。飞书侧交互效果采用
分析、选择、确认、结果四阶段卡片，不允许模型退回本机防火墙命令。

## 当前状态

截至 2026-08-07，本机联调已完成：

- Aegis HTTPS 工具网关运行于开发端口 18791；
- OpenClaw 插件 `aegis-tools` 版本为 `1.1.2`；
- 运行时已注册五个 `aegis_ip_*` 工具和 `/aegis-ip` 命令；
- 飞书消息中的 IPv4 会在模型运行前进入确定性卡片流程；
- 分析卡片已通过飞书真实发送验证；
- Aegis 已完成白名单账号的真实分析请求并生成批次；
- 已验证 dry-run 链路不会修改本机或远程防火墙；
- 飞书会话中的本机防火墙 `exec/process` 路径会被可信工具策略阻止；
- 未把本机 OpenClaw 配置、网关 token、证书私钥或飞书身份值写入仓库。

## 提交前验证

- 后端全量测试：`88 passed`；
- OpenClaw/安全响应/威胁情报专项测试：`21 passed`；
- 管理端 Node 安全测试：`1 passed`；
- Alembic 空 SQLite 数据库从首版升级到 `20260806_28 (head)`；
- 插件 `npm audit --omit=dev`：`0 vulnerabilities`；
- 插件 `npm run build` 和 `npm pack --dry-run` 成功；
- localhost 与 Tailscale 地址的 API、管理端、移动端和 18791 网关健康检查通过；
- Python 编译、Shell 语法和 `git diff --check` 通过。

## 本轮修复

1. 在插件 manifest 中声明 `contracts.tools`，解决插件显示已加载但运行时工具目录
   为空的问题。
2. 增加 `before_agent_reply` 卡片入口、`/aegis-ip` 卡片动作和五个远程工具。
3. 增加飞书本机防火墙命令阻止策略及提示词安全约束。
4. 修复 OpenClaw managed proxy 强制代理 `https://127.0.0.1:18791` 导致 TLS 在
   到达 Aegis 前断开的问题。`1.1.2` 对配置的精确 Aegis origin 使用独立直连，
   不改变全局代理策略。
5. 修复把“分析ip 66...”原样传给只接受纯 IP 的后端问题；现在统一提取并去重
   有效 IPv4。
6. 给卡片回复增加文本回退，避免卡片渲染失败时表现为完全无响应。
7. 固定 `undici 8.10.0`，依赖审计无已知漏洞；增加可重复的 build/prepack。

## 已确认的安全事实

- 旧会话曾读取本机防火墙状态，但没有写入规则；目标 IP 不在本机规则中。
- 所有卡片动作都会由 Aegis 后端重新校验飞书账号权限和批次所有权。
- 永久封禁必须来自显式卡片按钮，并受服务器总开关控制。
- 济南 IP 保留独立二次确认步骤。
- 当前没有自动解封能力，误封需要山石管理员人工删除并保留审计记录。

## 关键文件

- `code/backend/app/api/openclaw_tools.py`
- `code/backend/app/services/security_response.py`
- `code/openclaw-aegis-tools/index.ts`
- `code/openclaw-aegis-tools/openclaw.plugin.json`
- `docs/openclaw-remote-ip-tool-gateway.md`
- `docs/feishu-ip-security-response.md`

## 下一步

1. 按部署方案在正式 Aegis 服务器配置 18791 TLS、来源 CIDR 和 token。
2. 构建带校验和的版本化插件 tgz，并复制到远端 OpenClaw 服务器。
3. 在远端保留原有 `plugins.allow` 项，再追加 `aegis-tools`。
4. 完成未授权账号、只查询账号和封禁账号三类验收。
5. 先保持永久封禁关闭，通过 dry-run 后再安排批准的真实测试窗口。

## 部署入口

完整的服务器双端部署、验收、监控和回滚步骤见：

`docs/openclaw-remote-ip-tool-gateway.md`
