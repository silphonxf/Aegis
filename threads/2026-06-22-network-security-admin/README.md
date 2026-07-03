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
  - 当前分支是 `codex/persist-selfcheck-reports`，该分支已有远端提交 `116c2cd Persist selfcheck reports in database`；后续还有 Redis、日志路径、东八区时间戳、防火墙准备相关本地未提交改动。

## Firewall Blocking Prep

目标：对接服务器中的防火墙，把“IP 恶意研判”里的高危 IP 封禁动作接到真实防火墙地址组，先支持 dry-run，再支持真实封禁。

已有 Aegis 进度：

- `code/backend/app/services/firewall.py` 已存在，当前为未提交文件。
- `code/backend/app/api/admin.py` 的 `/api/v1/admin/threat-intel/block-ip` 已从 mock 切到 `block_ip_with_firewall(...)`，并把防火墙异常映射为：
  - `FIREWALL_CONFIG_MISSING` -> 503
  - `FIREWALL_REQUEST_FAILED` -> 502
  - `FIREWALL_BLOCK_INVALID` -> 400
- `code/backend/app/core/config.py` 已有防火墙环境变量：
  - `FIREWALL_RESTCONF_ENABLED`
  - `FIREWALL_RESTCONF_SCHEME`
  - `FIREWALL_RESTCONF_HOST`
  - `FIREWALL_RESTCONF_PORT`
  - `FIREWALL_RESTCONF_USERNAME`
  - `FIREWALL_RESTCONF_PASSWORD`
  - `FIREWALL_RESTCONF_VERIFY_SSL`
  - `FIREWALL_RESTCONF_TIMEOUT_SECONDS`
  - `FIREWALL_RESTCONF_VSYS`
  - `FIREWALL_ADDRESS_SET_NAME`
- 当前默认防火墙 host 是 `192.168.100.18`，地址组默认名是 `aegis-blocked-ip`，凭据仍需在 `.env` 中配置。

参考项目：

- TapeManage：`/home/xf/.codex/workspace/projects/TapeManage/home_application/views.py`
  - Hillstone/旧地址对象封禁：`cmd_block` / `cmd_unban`
    - SSH 后执行：`config -> address <地址组> -> ip <IP>/32 -> save`
    - 解禁：`config -> address <地址组> -> no ip <IP>/32`
  - 华为 FOC 地址组封禁：`encode_FOCip`
    - SSH 后执行：`sys -> ip address-set <地址组> type object -> address <IP> mask 32 -> quit -> quit -> save`
  - 华为 FOC 批量封禁：同一命令循环写入地址组。
- HiSecEngine YANG API：`/home/xf/.codex/workspace/projects/HiSecEngine_YANG_API_extracted`
  - 关键模块：`yang/huawei-address-set.html`
  - 关键列表：`yang/huawei-address-set_list_55ead4ec7e12c35b0cb1a808b49c8770.html`
  - 关键容器：`yang/huawei-address-set_container_e034df19540b34defa9a4f798bcbf88d.html`
  - RESTCONF/YANG 路径语义：
    - namespace: `urn:huawei:yang:huawei-address-set`
    - root: `/hw-address-set:address-set`
    - address object: `/hw-address-set:address-set/hw-address-set:address-objects/hw-address-set:address-object`
    - element: `/hw-address-set:address-set/hw-address-set:address-objects/hw-address-set:address-object/hw-address-set:elements/hw-address-set:element`
    - element fields include `elem-id`, `address-ipv4`, `mask`
  - 文档示例中 `address-object` 可用 `xc:operation="merge"`，元素示例包含：
    - `<elem-id>1</elem-id>`
    - `<address-ipv4>1.1.1.1</address-ipv4>`
    - `<mask>255.255.255.0</mask>`

当前 RESTCONF 设计假设：

- Aegis 使用 `PATCH` 写入 `huawei-address-set:address-set/address-objects/address-object=<address_set_name>`。
- 写入 body 包含：
  - `<address-object xmlns="urn:huawei:yang:huawei-address-set">`
  - `<name>{address_set_name}</name>`
  - `<elements><element><elem-id>...</elem-id><address-ipv4>{ip}</address-ipv4><mask>255.255.255.255</mask></element></elements>`
- 真实联调前需要用防火墙实际返回确认：
  - URL 是否需要 `huawei-vsys-instance:vsys-instance/vsyses/vsys=<vsys>/vsys-config/...` 前缀。
  - `PATCH` 到 address-object 是否会合并 elements，还是必须 PATCH 到 `elements/element=<elem-id>`。
  - `elem-id` 是否可由客户端指定，重复 IP 时是否幂等。
  - 是否需要显式 save/commit，还是 RESTCONF 写配置自动持久化。

## TapeManage Firewall Function Mapping

TapeManage 当前是通过 SSH 登录设备并发送 CLI 命令实现地址组变更。Aegis 后续要做同样能力，但实现方式改为 RESTCONF/API 调用，便于审计、重试、幂等和迁移。

TapeManage 现有功能：

| TapeManage 入口 | 代码位置 | 当前 SSH/CLI 行为 | 业务含义 | HiSecEngine API 映射 |
| --- | --- | --- | --- | --- |
| `encode_ip` | `home_application/views.py` | 调 `cmd_block`，执行 `config -> address <b_addr> -> ip <b_ip>/32 -> save` | 黑名单封禁 IP | 如果目标防火墙是华为，映射为向指定黑名单 `address-object` 增加 `element`：`address-ipv4=<b_ip>`，`mask=255.255.255.255` |
| `decode_ip` | `home_application/views.py` | 调 `cmd_unban`，执行 `config -> address <b_addr> -> no ip <b_ip>/32` | 黑名单解封 IP | 查找 `address-object` 中对应 IP 的 `elem-id`，再 DELETE 该 `element`，或 PATCH 删除语义，具体以实机 RESTCONF 支持为准 |
| `get_ip_list` / `search_ip` | `home_application/views.py` | 查询 `IpTable` 操作记录和当前地址组 | 封禁记录查询 | Aegis 应新增封禁记录表，接口查询 DB；地址组实时状态可用 GET RESTCONF 对账 |
| `encode_FOCip` | `home_application/views.py` | 执行 `sys -> ip address-set <b_addr> type object -> address <b_ip> mask 32 -> save` | FOC 地址组加白/加对象 | 映射为向 `<b_addr>` 对应的 `address-object` 增加 `element`，`mask=255.255.255.255` |
| `decode_FOCip` | `home_application/views.py` | 当前代码和 `encode_FOCip` 一样仍发送 `address <b_ip> mask 32` | 名称是撤销，但实现看起来仍是添加地址；需实机/业务确认 | 如果实际是撤销，应改为 DELETE 对应 `element`；如果实际业务是“再次写入白名单”，则保持 add 行为 |
| FOC Excel 批量导入 | `home_application/views.py` | 循环执行 `ip address-set <b_addr> type object -> address <ip> mask 32 -> save` | 批量写入地址组 | API 层应批量构造多个 `element`，优先一次 PATCH；若设备不支持多元素合并，则逐 IP PATCH 并记录每条结果 |

HiSecEngine/YANG 对应关系：

| CLI 概念 | RESTCONF/YANG 节点 |
| --- | --- |
| `ip address-set <b_addr> type object` / `address <b_addr>` | `/hw-address-set:address-set/hw-address-set:address-objects/hw-address-set:address-object[name=<b_addr>]` |
| `address <ip> mask 32` 或 `ip <ip>/32` | `/elements/element` 下的 `address-ipv4=<ip>`、`mask=255.255.255.255` |
| 单条地址唯一标识 | `elem-id`，Aegis 需要先 GET 现有元素，重复 IP 复用原 `elem-id`，新增 IP 使用下一个可用 ID |
| CLI `save` | RESTCONF 是否自动持久化待实机确认；如果设备要求 commit/save，需要再查 RPC 或厂商扩展接口 |

建议的 Aegis API 设计：

1. `POST /api/v1/admin/firewall/address-sets/{address_set}/entries`：单 IP 加入地址组，支持 `dry_run`。
2. `DELETE /api/v1/admin/firewall/address-sets/{address_set}/entries/{ip}`：从地址组移除 IP。
3. `POST /api/v1/admin/firewall/address-sets/{address_set}/entries:batch`：批量加入地址组，返回每个 IP 的结果。
4. `GET /api/v1/admin/firewall/address-sets/{address_set}/entries`：读取防火墙实际地址组，供对账和下拉详情使用。
5. `GET /api/v1/admin/firewall/block-records`：查询本地封禁/解封审计记录。

Postman 直连防火墙封禁 IP 请求草案：

```http
PATCH https://192.168.100.18:8443/restconf/data/huawei-vsys-instance:vsys-instance/vsyses/vsys=public/vsys-config/huawei-address-set:address-set/address-objects/address-object=aegis-blocked-ip
Authorization: Basic <base64(username:password)>
Accept: application/yang-data+xml
Content-Type: application/yang-data+xml
```

Body:

```xml
<address-object xmlns="urn:huawei:yang:huawei-address-set">
  <name>aegis-blocked-ip</name>
  <description>Aegis blocked IP address set</description>
  <elements>
    <element>
      <elem-id>1</elem-id>
      <description>Aegis block 203.0.113.10</description>
      <address-ipv4>203.0.113.10</address-ipv4>
      <mask>255.255.255.255</mask>
    </element>
  </elements>
</address-object>
```

Postman 配置：

- Method: `PATCH`
- Auth: `Basic Auth`，填防火墙 RESTCONF 用户名和密码。
- Headers: `Accept=application/yang-data+xml`，`Content-Type=application/yang-data+xml`。
- Body: `raw`，类型选 `XML`。
- SSL: 如果是自签证书，Postman 里先关闭 `SSL certificate verification`。
- 变量替换：把 `192.168.100.18`、`8443`、`public`、`aegis-blocked-ip`、`203.0.113.10` 换成实机值。

注意：`elem-id=1` 只能用于首次测试。真实封禁前应先 GET 该地址组，确认已有最大 `elem-id` 和目标 IP 是否已存在；否则可能覆盖/冲突。当前 Aegis `firewall.py` 已按“先 GET，再选择 elem-id，再 PATCH”的方式设计。

如果实机不接受带 `huawei-vsys-instance` 前缀的 URL，备用 URL 是：

```http
PATCH https://192.168.100.18:8443/restconf/data/huawei-address-set:address-set/address-objects/address-object=aegis-blocked-ip
```

如果实机要求 PATCH 到元素集合，备用 URL 是：

```http
PATCH https://192.168.100.18:8443/restconf/data/huawei-vsys-instance:vsys-instance/vsyses/vsys=public/vsys-config/huawei-address-set:address-set/address-objects/address-object=aegis-blocked-ip/elements
```

对应 body 可缩小为：

```xml
<elements xmlns="urn:huawei:yang:huawei-address-set">
  <element>
    <elem-id>1</elem-id>
    <description>Aegis block 203.0.113.10</description>
    <address-ipv4>203.0.113.10</address-ipv4>
    <mask>255.255.255.255</mask>
  </element>
</elements>
```

## Key Files

- `code/frontend-admin/index.html`
- `code/frontend-admin/app.js`
- `code/frontend-admin/js/toolbox.js`
- `code/frontend-admin/js/threatbook.js`
- `code/backend/app/api/toolbox.py`
- `code/backend/app/api/admin.py`
- `code/backend/app/services/firewall.py`
- `code/backend/app/core/config.py`
- `/home/xf/.codex/workspace/projects/TapeManage/home_application/views.py`
- `/home/xf/.codex/workspace/projects/HiSecEngine_YANG_API_extracted/yang/huawei-address-set.html`

## Decisions

- 本次不改后端接口，仅在管理端复用已有移动端工具接口，降低联调风险。
- IP 研判保留原 ThreatBook 脚本和后端接口，只移动导航归属与展示标题。
- 新增页面采用现有 `card`、`summary-strip`、`grid2`、`pre` 样式，保持管理端视觉一致。
- 防火墙封禁优先走华为 RESTCONF 地址集；TapeManage 的 SSH 命令作为回退/对照，不优先直接复用。
- 真实封禁默认应保留 `dry_run=true`，联调确认 URL、body、认证和保存语义后再允许管理端执行真实封禁。

## Next Steps

- 按实际使用反馈调整 Ping 输出摘要和异常状态样式。
- 抓包工具可继续补“请求头/方法/Body”等高级输入。
- IP 恶意研判后续可拆出本地规则、ThreatBook、封禁审批三个子视图。
- 防火墙联调下一步：
  1. 在 `.env` 配置真实 `FIREWALL_RESTCONF_USERNAME` / `FIREWALL_RESTCONF_PASSWORD` / `FIREWALL_ADDRESS_SET_NAME`。
  2. 用 `dry_run=true` 调 `/api/v1/admin/threat-intel/block-ip`，确认 URL 和 XML body。
  3. 用只读 GET 验证防火墙 RESTCONF 地址集路径是否正确。
  4. 在测试 IP 上执行真实 PATCH，确认地址组新增、重复执行幂等、审计日志记录。
  5. 视联调结果补 DELETE/解封能力和封禁记录表。

## Handoff

打开管理端后，从左侧“网络安全”进入三个子功能。若需要继续调整某个功能，请在本 thread 中说明具体目标。
