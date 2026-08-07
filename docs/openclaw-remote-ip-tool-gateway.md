# OpenClaw 远程 IP 插件网关部署方案

## 1. 目标与边界

本方案把 Aegis 部署为唯一的 IP 研判与防火墙变更入口，供另一台服务器上的
OpenClaw 飞书机器人调用。OpenClaw 不直接登录山石设备，也不使用本机
`iptables`、`nft`、`ufw`、`firewall-cmd` 或路由黑洞作为兜底。

```text
飞书用户
  -> OpenClaw 服务器 + openclaw-aegis-tools
  -> HTTPS /aegis/tools/v1/*
  -> Aegis 网关服务器 :18791
  -> Aegis API + 飞书 open_id 白名单
  -> 威胁情报 / 山石地址簿
```

交互采用确定性的卡片状态机：

```text
分析 IP -> 选择建议封禁/全部恶意 -> 济南二次确认（按需）
        -> 仅演练/确认永久封禁 -> 结果卡片
```

永久封禁必须同时满足：

1. 请求来自配置允许的 OpenClaw 服务器地址；
2. Bearer token 正确；
3. OpenClaw 可信上下文中的渠道为 `feishu`；
4. 飞书 `open_id` 已启用且拥有 `can_block`；
5. 批次属于同一个飞书账号且未过期；
6. Aegis 服务器已开启永久封禁总开关；
7. 用户点击了卡片中的永久封禁确认按钮。

模型不能填写或覆盖 `open_id`。插件从 OpenClaw 可信运行上下文读取发送者身份，
再通过请求头转发给 Aegis。

## 2. 推荐网络拓扑

推荐两台服务器通过内网或 Tailscale 通信，不把 18791 暴露到公网。

| 节点 | 职责 | 入站要求 |
| --- | --- | --- |
| Aegis 网关服务器 | API、权限、审计、威胁情报、防火墙适配 | 仅允许 OpenClaw 服务器访问 TCP 18791 |
| OpenClaw 服务器 | 飞书接入、卡片渲染、插件运行 | 能访问飞书、模型服务和 Aegis 18791 |
| 山石设备 | 最终地址簿变更 | 仅允许 Aegis 后端访问管理接口 |

Aegis API 建议只监听 `127.0.0.1:8000`，由 Nginx 在 18791 终止 TLS。若现有
Aegis API 本身使用 HTTPS，Nginx 的 `proxy_pass` 相应改为
`https://127.0.0.1:8000` 并配置内部证书校验。

## 3. Aegis 网关服务器部署

### 3.1 更新代码与数据库

以下示例假设仓库位于 `/opt/Aegis`，虚拟环境位于 `/opt/Aegis/.venv`：

```bash
cd /opt/Aegis
git pull --ff-only

/opt/Aegis/.venv/bin/pip install -r code/backend/requirements.txt
cd code/backend
../../.venv/bin/alembic upgrade head
```

本功能包含安全响应表、飞书身份白名单和目标字段修复迁移。升级前应先备份数据库。

### 3.2 配置环境变量

在服务器密钥文件或 systemd `EnvironmentFile` 中设置，不要写入仓库：

```dotenv
OPENCLAW_TOOL_GATEWAY_ENABLED=true
OPENCLAW_TOOL_GATEWAY_TOKEN=<至少 32 字节的随机值>
OPENCLAW_TOOL_ALLOWED_CLIENT_CIDRS=<OPENCLAW_SERVER_IP>/32
OPENCLAW_TOOL_FIREWALL_TARGET_CODE=test-primary
OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK=false
```

生成 token：

```bash
openssl rand -hex 32
```

首轮部署必须保持 `OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK=false`。完成白名单、目标
设备和 dry-run 验收后，才可在批准的维护窗口中改为 `true`。

`OPENCLAW_TOOL_ALLOWED_CLIENT_CIDRS` 支持逗号分隔的 IPv4/IPv6 CIDR。生产
环境不得留空。反向代理必须覆盖客户端传入的 `X-Aegis-Proxy-Client-IP`，不能
透传该请求头，否则来源地址校验可能被伪造。

### 3.3 配置 18791 HTTPS 反向代理

生产环境推荐使用 Nginx，而不是开发脚本 `scripts/serve_https.py`。示例：

```nginx
server {
    listen 18791 ssl;
    server_name aegis-gateway.internal.example;

    ssl_certificate     /etc/aegis/tls/fullchain.pem;
    ssl_certificate_key /etc/aegis/tls/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 2m;
    access_log /var/log/nginx/aegis-tool-gateway.access.log;
    error_log  /var/log/nginx/aegis-tool-gateway.error.log warn;

    allow <OPENCLAW_SERVER_IP>;
    deny all;

    location ^~ /aegis/tools/v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Request-ID $request_id;
        proxy_set_header X-Aegis-Proxy-Client-IP $remote_addr;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header X-OpenClaw-Channel $http_x_openclaw_channel;
        proxy_set_header X-Feishu-Open-Id $http_x_feishu_open_id;
        proxy_set_header X-OpenClaw-Session-Key $http_x_openclaw_session_key;
        proxy_set_header X-OpenClaw-Account-Id $http_x_openclaw_account_id;
        proxy_connect_timeout 5s;
        proxy_read_timeout 35s;
        proxy_send_timeout 35s;
        add_header Cache-Control "no-store" always;
    }

    location / {
        return 404;
    }
}
```

检查并加载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

主机防火墙也应限制来源，例如：

```bash
sudo ufw allow from <OPENCLAW_SERVER_IP> to any port 18791 proto tcp
```

不要仅依赖应用 token 保护公网监听端口。

### 3.4 启动与健康检查

重启 Aegis API 后检查：

```bash
sudo systemctl restart aegis-api
sudo systemctl status aegis-api --no-pager
curl --fail --cacert /etc/aegis/tls/ca.crt \
  https://aegis-gateway.internal.example:18791/aegis/tools/v1/healthz
```

预期返回：

```json
{"status":"ok","service":"aegis-openclaw-tool-gateway","enabled":true}
```

### 3.5 配置飞书账号白名单

登录 Aegis 管理端，在威胁情报页面的“飞书安全响应权限”中配置：

- `enabled=true`：身份进入白名单；
- `can_query=true`：允许 IP 研判；
- `can_block=true`：允许选择、确认和执行封禁；
- 授予 `can_block` 时必须绑定启用中的 Aegis `admin` 或 `super_admin` 用户。

未知飞书账号首次出现时只会登记为禁用，不会自动获得查询或封禁权限。不要按
显示名称授权，只按飞书 `open_id` 与 Aegis 管理员绑定授权。

## 4. 构建和发布 OpenClaw 插件

在可信构建机或 Aegis 仓库中执行：

```bash
cd /opt/Aegis/code/openclaw-aegis-tools
npm ci
npm audit --omit=dev
npm pack
sha256sum openclaw-aegis-tools-*.tgz
```

`prepack` 会自动编译 `dist/index.js`。把版本化 tgz 和 SHA-256 通过受控渠道复制到
OpenClaw 服务器，不复制 `.env`、OpenClaw 配置、token 或私钥。

当前已联调版本为 `1.1.2`。该版本包含：

- 五个声明式远程工具契约；
- `/aegis-ip` 飞书卡片命令；
- IPv4 消息的模型前确定性拦截和卡片响应；
- OpenClaw 全局代理开启时，对已配置 Aegis origin 的独立直连；
- 中文消息到纯 IP 列表的规范化；
- 卡片发送失败时的文本回退；
- 飞书会话本机防火墙命令拦截策略。

## 5. OpenClaw 服务器安装

### 5.1 安装插件

```bash
openclaw plugins install ./openclaw-aegis-tools-1.1.2.tgz
```

升级已有版本时使用：

```bash
openclaw plugins install --force ./openclaw-aegis-tools-1.1.2.tgz
```

### 5.2 配置插件

在 OpenClaw 配置中加入：

```json5
{
  plugins: {
    // 在原有 allow 列表上追加，不要覆盖服务器已有插件。
    allow: ["aegis-tools", "feishu"],
    entries: {
      "aegis-tools": {
        enabled: true,
        hooks: {
          allowConversationAccess: true,
        },
        config: {
          baseUrl: "https://aegis-gateway.internal.example:18791",
          token: "<与 Aegis 相同的 token>",
          caFile: "/etc/openclaw/aegis-ca.crt",
          timeoutMs: 30000,
        },
      },
    },
  },
  tools: {
    alsoAllow: ["aegis-tools"],
  },
}
```

注意：

- `plugins.allow` 是全局插件白名单，必须保留现有条目；
- `hooks.allowConversationAccess=true` 是读取可信飞书发送者上下文所必需；
- 生产环境必须使用可信证书或私有 CA；
- `allowInsecureTls: true` 只允许用于封闭网络的短期联调；
- token 所在配置文件权限应为 `0600`，并纳入服务器密钥备份与轮换流程；
- 远端部署时 `baseUrl` 不能写 `127.0.0.1`，必须指向 Aegis 网关地址。

插件 `1.1.2` 使用独立 Undici dispatcher 直连配置的精确 Aegis origin，因此不会
被 OpenClaw 的全局模型代理错误转发，也不会放宽其他插件的代理策略。

### 5.3 重启并验证注册

```bash
systemctl --user restart openclaw-gateway.service
systemctl --user status openclaw-gateway.service --no-pager
openclaw plugins inspect aegis-tools
openclaw gateway call tools.catalog \
  --params '{"agentId":"main","includePlugins":true}'
openclaw gateway call commands.list
```

必须看到以下五个工具：

- `aegis_ip_capabilities`
- `aegis_ip_analyze`
- `aegis_ip_prepare_block`
- `aegis_ip_confirm_jinan`
- `aegis_ip_execute_block`

命令列表必须包含 `aegis-ip`，日志应包含：

```text
aegis-tools: registered 5 remote tools, card workflow, and local-firewall guard
```

## 6. 分阶段验收

### 阶段 A：连接和拒绝策略

1. 从 OpenClaw 服务器请求 `/healthz`，确认 TLS 与网络连通。
2. 使用未授权飞书账号发送 IP，确认 Aegis 返回拒绝卡片。
3. 使用只有 `can_query` 的账号分析 IP，确认能看到分析卡片但不能执行封禁。
4. 尝试让 OpenClaw 使用 `exec` 调用本机防火墙命令，确认被插件策略阻止。

### 阶段 B：授权账号 dry-run

1. 授权测试账号 `enabled=true, can_query=true, can_block=true`。
2. 在飞书发送：`分析 IP 66.240.205.34`。
3. 确认出现分析卡片，而不是模型自由回答。
4. 点击“选择建议封禁”。
5. 点击“仅演练（不改防火墙）”。
6. 确认结果卡片显示 dry-run 成功，并在山石地址簿核对没有变化。

### 阶段 C：永久封禁

只有在变更审批、目标设备、地址簿引用关系和回滚人员均确认后才执行：

1. 将 `OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK=true` 并重启 Aegis API；
2. 选择不会影响业务的批准测试 IP；
3. 从卡片点击“确认永久封禁”；
4. 在山石控制台回读地址簿；
5. 核对 Aegis 审计日志中的请求人、批次、目标和结果；
6. 测试结束后按管理要求恢复永久封禁总开关。

包含济南 IP 的批次必须额外出现济南二次确认卡片。跳过该步骤时，后端状态机
必须拒绝执行。

## 7. 监控与审计

建议监控：

- `https://<AEGIS_GATEWAY>:18791/aegis/tools/v1/healthz`；
- Aegis API systemd 状态与错误率；
- Nginx 18791 的 401、403、409、5xx；
- OpenClaw 日志中的 `aegis-tools analysis card failed`；
- 飞书卡片命令失败；
- 山石地址簿写入后的回读不一致；
- 白名单、封禁批次和永久封禁的 Aegis 审计记录。

日志中不得记录 Bearer token、飞书 App Secret、山石密码或完整 Authorization
请求头。token 应定期轮换；轮换时先更新 Aegis，再立即更新 OpenClaw 并重启，
完成后验证旧 token 已失效。

## 8. 回滚

### 立即停止远程操作

```dotenv
OPENCLAW_TOOL_GATEWAY_ENABLED=false
OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK=false
```

重启 Aegis API后，远程工具请求将被拒绝。

### 停用 OpenClaw 插件

```bash
openclaw config set plugins.entries.aegis-tools.enabled false --json
systemctl --user restart openclaw-gateway.service
```

也可以重新安装部署前保留的上一版本 tgz。不要为了回滚插件而清空
`plugins.allow` 或覆盖其他插件配置。

### 回滚误封

当前功能只实现永久加入地址簿，没有自动解封。误封时由山石管理员从对应地址簿
人工删除 IP，回读验证策略结果，并在 Aegis 审计中记录人工回滚。数据库迁移为
增量迁移；代码回滚通常保留新增表，不建议在应急时直接执行破坏性 downgrade。

## 9. 上线清单

- [ ] Aegis 数据库已备份并迁移到最新版本
- [ ] 18791 使用可信 TLS，且仅允许 OpenClaw 服务器访问
- [ ] token 长度、存储权限和轮换负责人已确认
- [ ] `OPENCLAW_TOOL_ALLOWED_CLIENT_CIDRS` 非空且准确
- [ ] OpenClaw 插件版本及 tgz SHA-256 已记录
- [ ] 五个工具和 `/aegis-ip` 已在运行时注册
- [ ] 未授权账号、只查询账号和封禁账号均已测试
- [ ] 本机防火墙命令拦截已测试
- [ ] dry-run 已通过且山石无变化
- [ ] 济南二次确认已测试
- [ ] 永久封禁总开关默认关闭
- [ ] 监控、审计和人工解封负责人已明确
