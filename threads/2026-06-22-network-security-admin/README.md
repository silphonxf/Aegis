# Network Security Admin Module

## Goal

在管理端新增“网络安全”模块，集中承接移动端网络排障与安全研判能力：Ping 工具、抓包分析、IP 恶意研判。后续在这个 thread 中继续逐项调整每个功能。

## Current State

- 管理端侧边栏新增“网络安全”分组。
- Ping 工具新增管理端页面，复用 `/api/v1/toolbox/ping`。
- 抓包分析新增管理端页面，复用 `/api/v1/toolbox/capture/fetch` 与 `/api/v1/toolbox/capture/analyze`。
- 原“高危IP研判”入口从“运维审批与审计”移入“网络安全”，页面标题调整为“IP 恶意研判”，原 ThreatBook 能力保持不变。
- 2026-07-01 进度补充：
  - Redis 已安装并启动，本地 `redis-cli ping` 返回 `PONG`。
  - 原 `emergency_ops.json` 已导入当前 Aegis 数据库；应急配置、系统列表、系统日志配置已接入 Redis 缓存。
  - 系统日志路径已写入 `system_log_configs`：当前 3 个系统各配置了 Aegis 本机 backend/admin/mobile 日志路径。
  - AI 自检报告 `checked_at` 已调整为东八区格式，例如 `2026-07-01T10:44:20+08:00`。
  - 自检报告持久化已从本地 JSON 文件迁到数据库 `selfcheck_reports`。

## Hillstone Firewall Blocking

2026-07-03 修正：防火墙不是华为 USG，而是山石 StoneOS。Aegis 封禁实现改为山石 REST API。

目标：对接服务器中的山石防火墙，把“IP 恶意研判”里的高危 IP 封禁动作接到真实防火墙地址簿。第一版按 TapeManage 旧流程实现：

```text
config
address <地址簿名>
ip <IP>/32
save
```

Aegis REST 实现等价为：

1. `POST https://<firewall>/rest/api/login` 登录，用户名和密码按山石 Python 示例做 Base64。
2. 从登录响应中取 `token`、`role`、`vsysId`、`fromrootvsys`，作为后续请求 cookie。
3. `GET https://<firewall>/rest/api/addrbook?query=...` 查询目标地址簿当前 `member`。
4. 把待封禁 IP 合并成 `IP/32` 追加到 `member`，再尝试 `PUT https://<firewall>/rest/api/addrbook` 更新。

已有 Aegis 进度：

- `code/backend/app/services/firewall.py` 已切换为 `HillstoneRestClient`。
- `code/backend/app/api/admin.py` 的 `/api/v1/admin/threat-intel/block-ip` 继续复用同一个入口。
- dry-run 会返回登录请求和地址簿更新请求，不会调用防火墙。
- 真实执行时会先登录、查询地址簿、合并 `member`，再更新地址簿。
- 配置项已改为：
  - `HILLSTONE_ENABLED`
  - `HILLSTONE_SCHEME`
  - `HILLSTONE_HOST`
  - `HILLSTONE_PORT`
  - `HILLSTONE_USERNAME`
  - `HILLSTONE_PASSWORD`
  - `HILLSTONE_VERIFY_SSL`
  - `HILLSTONE_TIMEOUT_SECONDS`
  - `HILLSTONE_ADDRESS_BOOK_NAME`
  - `HILLSTONE_ADDRBOOK_PATH`
  - `HILLSTONE_ADDRBOOK_METHOD`
  - `HILLSTONE_ADDRBOOK_TYPE`

参考资料：

- 山石 Python 示例：`/home/xf/山石防火墙/python-restapi.py`
  - 登录：`POST /rest/api/login`
  - 登录 payload：`lang`、Base64 后的 `userName`、Base64 后的 `password`
  - 后续请求：使用登录返回的 cookie
- 山石 RESTful API 手册目录：`/home/xf/山石防火墙/index.html`
  - 目录中包含“静态IP黑名单”“动态IP黑名单”“地址簿”
- TapeManage：`/home/xf/.codex/workspace/projects/TapeManage/home_application/views.py`
  - `cmd_block`: `config -> address <b_addr> -> ip <b_ip>/32 -> save`
  - `cmd_unban`: `config -> address <b_addr> -> no ip <b_ip>/32`

## Postman Test

### 1. Login

```http
POST https://192.168.100.18/rest/api/login
Content-Type: application/json
```

Body:

```json
{
  "lang": "zh_CN",
  "userName": "<base64(username)>",
  "password": "<base64(password)>"
}
```

示例：如果用户名是 `hillstone`，Base64 是 `aGlsbHN0b25l`。密码也需要按同样方式转换。

登录成功后，从响应的 `result[0]` 取：

```json
{
  "token": "...",
  "role": "...",
  "vsysId": "...",
  "fromrootvsys": "..."
}
```

### 2. Query Address Book

```http
GET https://10.67.82.6/rest/api/addrbook?query=%7B%22start%22%3A0%2C%22limit%22%3A500%7D
Cookie: token=<token>; role=<role>; vsysId=<vsysId>; fromrootvsys=<fromrootvsys>; username=<username>
```

2026-07-04 实机确认：`addrbook` 返回结构使用 `member` 数组，不使用顶层 `ip` / `netmask` 字段。

```json
{
  "name": "xdr_soar_in_v4",
  "member": ["216.250.248.88/32", "16.163.96.158/32"],
  "is_ipv6": "0",
  "is_ordered": "0",
  "predefined": "0"
}
```

### 3. Add IP To Address Book

候选请求 1：collection URL + 数组 body。待 admin 权限账号验证。

```http
PUT https://10.67.82.6/rest/api/addrbook
Content-Type: application/json
Cookie: token=<token>; role=<role>; vsysId=<vsysId>; fromrootvsys=<fromrootvsys>; username=<username>
```

Body 必须保留当前已有 `member`，再追加新 IP，避免覆盖地址簿：

```json
[
  {
    "name": "xdr_soar_in_v4",
    "member": ["216.250.248.88/32", "16.163.96.158/32", "203.0.113.10/32"]
  }
]
```

候选请求 2：命名 URL + 对象 body。2026-07-04 operator 角色实测返回 `success:true`，但查询 `xdr_soar_in_v4` 未看到新增成员，因此记录为未生效候选。

```http
PUT https://10.67.82.6/rest/api/addrbook/xdr_soar_in_v4
Content-Type: application/json
Cookie: token=<token>; role=<role>; vsysId=<vsysId>; fromrootvsys=<fromrootvsys>; username=<username>
```

```json
{
  "name": "xdr_soar_in_v4",
  "member": ["216.250.248.88/32", "16.163.96.158/32", "203.0.113.10/32"]
}
```

已排除的错误 body：

- 顶层 `ip` + `netmask` 返回 `Index object netmask of ip can not be empty`。
- 顶层 `ip` + `netmask: 32` 返回 `Index object netmask of ip can not be empty`。
- 嵌套 `ip: {ip, netmask}` 返回 `"ip" is invalid element`。
- 带 `is_ordered: "0"` 的 PUT 返回 `Invalid is_ordered: "0"`。

后续有 admin 权限后继续验证：

```text
HILLSTONE_HOST=10.67.82.6
HILLSTONE_ADDRESS_BOOK_NAME=xdr_soar_in_v4
```

Bruno 请求模板已保存到：

```text
threads/2026-06-22-network-security-admin/bruno/hillstone-firewall
```

## Aegis Dry Run

管理端“一键封禁”仍调用：

```http
POST https://<aegis-backend>:8000/api/v1/admin/threat-intel/block-ip
Authorization: Bearer <admin-token>
Content-Type: application/json
```

Body:

```json
{
  "ip": "203.0.113.10",
  "risk_level": "high_risk",
  "reason": "Postman test",
  "source": "threatbook",
  "dry_run": true
}
```

返回中会包含山石登录请求和地址簿更新请求的 URL/body。

## Key Files

- `code/frontend-admin/index.html`
- `code/frontend-admin/app.js`
- `code/frontend-admin/js/toolbox.js`
- `code/frontend-admin/js/threatbook.js`
- `code/backend/app/api/toolbox.py`
- `code/backend/app/api/admin.py`
- `code/backend/app/services/firewall.py`
- `code/backend/app/core/config.py`
- `threads/2026-06-22-network-security-admin/bruno/hillstone-firewall`
- `/home/xf/.codex/workspace/projects/TapeManage/home_application/views.py`
- `/home/xf/山石防火墙/python-restapi.py`
- `/home/xf/山石防火墙/index.html`

## Decisions

- 管理端入口保持不变，继续由“IP 恶意研判”触发 `/api/v1/admin/threat-intel/block-ip`。
- 封禁后端实现从华为 RESTCONF 改为山石 StoneOS REST API。
- 第一版优先复刻 TapeManage 的地址簿封禁逻辑，而不是直接切静态黑名单模块，避免和现有防火墙策略引用方式不一致。
- 真实封禁默认应保留 `dry_run=true`，确认 admin 权限下 `PUT /rest/api/addrbook` 能真实更新 `member` 后再允许真实封禁。
- 账号 `fengjin` 当前登录角色为 `operator`；`PATCH /rest/api/addrbook/xdr_soar_in_v4` 返回 `Sorry, you do not have privilege to do this`。该账号可能无修改地址簿成员权限，或 `PUT` 在 operator 下返回 `success:true` 但不落配置。

## Next Steps

- 有 admin 权限后，用 Bruno 先验证 `PUT /rest/api/addrbook` 数组 body 是否能把测试 IP 写入 `xdr_soar_in_v4.member`。
- 若 admin 权限下仍不生效，改测山石“动态IP黑名单”或 CLI/API save/commit 流程。
- 将 `.env` 的 `HILLSTONE_ADDRESS_BOOK_NAME` 改为实际被策略引用的地址簿名，例如 `xdr_soar_in_v4`。
- 用 `dry_run=true` 调 `/api/v1/admin/threat-intel/block-ip`，确认 Aegis 生成的请求和 Postman 一致。
- 视实机结果补解封能力：删除地址簿里的 IP/32。
- 增加本地封禁/解封审计记录表，替代 TapeManage 的 `IpTable` 记录方式。

## Handoff

打开管理端后，从左侧“网络安全”进入三个子功能。若继续调防火墙，先用 dry-run 取 Aegis 生成的请求，再用 Postman 在山石实机上验证登录和地址簿更新。
