# Aegis 系统状态管理端配置设计（初稿）

## 1. 背景

当前 Aegis 的“系统状态”能力主要基于两类数据来源：

1. **本机采集**：通过 `/monitoring/collect/local` 读取当前 Aegis 后端宿主机的 CPU、内存、磁盘、端口状态，并写入 `system_status_snapshots`。
2. **外部上报**：通过 `/systems/{system_id}/status/snapshot` 由外部脚本、探针或其他服务向指定系统写入状态快照。

当前实现能够满足“有一份系统状态快照并在首页展示”的基础需求，但还存在以下问题：

- 用户可见系统范围尚未按“用户-系统”收敛，默认是全量系统。
- 状态采集目标缺少管理端配置入口，无法明确区分“宿主机状态”“应用服务状态”“网络连通性状态”。
- 状态规则目前主要是全局阈值，缺少按系统差异化配置能力。
- 状态来源与采集方式没有结构化建模，后续扩展 SSH、HTTP、Agent 上报会比较散。

因此需要补充一套“系统状态管理端配置”设计，使其具备可配置、可授权、可审计、可扩展的能力。

---

## 2. 设计目标

本设计初稿的目标如下：

1. **明确用户能看哪些系统**：系统状态展示范围应按用户授权收敛，而不是默认全量可见。
2. **明确系统状态看什么**：可区分宿主机资源、端口存活、HTTP 探活、巡检结果、自检结果等不同维度。
3. **支持管理端配置**：可通过管理端配置系统状态采集对象、采集方式、采集规则、展示规则。
4. **支持逐步演进**：先支持本机采集 / HTTP / 端口 / 上报，后续再扩展 SSH、Agent、批量采集等能力。
5. **支持审计**：所有关键配置修改都应可追踪。

---

## 3. 当前实现现状

### 3.1 当前“用户看哪些系统”

当前 overview 逻辑本质上是：

```python
systems = db.query(System).all()
```

这意味着：

- 已登录用户可以看到 `systems` 表中的全部系统。
- 当前只有功能级角色控制（如 admin、super_admin），没有系统级可见范围控制。
- 暂未建立用户与系统的授权关系模型。

### 3.2 当前“系统状态”是什么

当前系统状态实际是“系统 + 最近一条状态快照”的展示结果。

状态快照来源主要有两类：

#### A. 本机采集

`/monitoring/collect/local` 采集的是当前 Aegis 后端所在宿主机：

- CPU
- 内存
- 磁盘
- `127.0.0.1:8000` 端口
- 当前主机名

所以这条链路本质上表示的是：

**Aegis 所在宿主机状态**，不是通用意义上的“任意业务系统状态”。

#### B. 外部快照上报

`/systems/{system_id}/status/snapshot` 允许外部脚本、探针或其他服务向指定系统写入快照。

因此目前的后端并不一定主动探测每个系统，更多是：

- 要么采集本机
- 要么接收上报

---

## 4. 演进原则

### 4.1 用户可见范围与状态采集配置解耦

“谁能看这个系统”与“这个系统怎么采状态”是两件事，应拆开建模。

- 用户可见范围：解决访问控制
- 状态采集配置：解决数据来源与采集方式

### 4.2 系统状态不等于宿主机状态

后续管理端配置中，必须允许一个系统同时拥有多种状态维度：

- 宿主机资源状态
- 应用服务存活状态
- 端口状态
- HTTP 健康检查状态
- 巡检结果
- 自检结果
- 日志异常状态（可选）

### 4.3 先统一模型，再逐步扩展采集器

建议先把“系统状态目标”“采集方式”“规则”“可见范围”设计清楚，再逐步落地：

第一阶段建议支持：
- local（本机）
- tcp（端口）
- http（URL 探活）
- push（外部上报）

后续再考虑：
- ssh（远程采集）
- agent（节点代理）
- batch（批量任务）

---

## 5. 核心数据模型建议

### 5.1 用户-系统授权关系表

#### `user_system_roles`

用于定义某个用户在某个系统上的可见权限与操作权限。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键 |
| user_id | bigint | 用户 ID |
| system_id | bigint | 系统 ID |
| role_code | varchar(32) | 角色编码，如 viewer/operator/admin |
| can_view_status | boolean | 是否可查看系统状态 |
| can_view_logs | boolean | 是否可查看系统日志 |
| can_trigger_collect | boolean | 是否可手动触发状态采集 |
| can_manage_status_config | boolean | 是否可管理状态配置 |
| is_active | boolean | 是否生效 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

> 说明：这里可以和日志权限设计保持一致，后续让“状态”和“日志”共享同一套用户-系统授权模型。

---

### 5.2 系统状态采集目标表

#### `system_status_targets`

定义一个系统有哪些状态采集目标。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键 |
| system_id | bigint | 所属系统 |
| target_name | varchar(128) | 目标名称，如“生产主机”“前端服务”“后端健康检查” |
| target_type | varchar(32) | 目标类型：host/service/url/port/push |
| collector_type | varchar(32) | 采集方式：local/tcp/http/push/ssh/agent |
| host | varchar(255) | 主机/IP，可空 |
| port | int | 端口，可空 |
| url | varchar(512) | 健康检查 URL，可空 |
| path | varchar(255) | 资源路径，如磁盘路径 `/data`，可空 |
| env | varchar(32) | 环境，如 prod/test/dev |
| weight | int | 权重，用于整体状态汇总 |
| enabled | boolean | 是否启用 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

> 一个系统可以配置多个 target，例如：
> - 一个用于检查宿主机 CPU/内存/磁盘
> - 一个用于检查 8000 端口
> - 一个用于检查 `/healthz`

---

### 5.3 系统状态规则表

#### `system_status_rules`

定义某个系统或某个 target 的状态阈值与判定规则。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键 |
| system_id | bigint | 系统 ID，可空 |
| target_id | bigint | 目标 ID，可空 |
| cpu_warn | int | CPU 告警阈值 |
| cpu_critical | int | CPU 严重阈值 |
| mem_warn | int | 内存告警阈值 |
| mem_critical | int | 内存严重阈值 |
| disk_warn | int | 磁盘告警阈值 |
| disk_critical | int | 磁盘严重阈值 |
| response_ms_warn | int | HTTP 响应告警阈值 |
| response_ms_critical | int | HTTP 响应严重阈值 |
| fail_count_warn | int | 连续失败告警次数 |
| fail_count_critical | int | 连续失败严重次数 |
| enabled | boolean | 是否启用 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

> 建议支持三层优先级：
> 1. target 级规则
> 2. system 级规则
> 3. 全局默认规则

---

### 5.4 系统状态快照扩展表（延续当前快照）

当前已有：`system_status_snapshots`

建议后续扩展字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| target_id | bigint | 来自哪个采集目标 |
| collector_type | varchar(32) | 本次采集方式 |
| response_ms | int | HTTP 响应时间 |
| http_status | int | HTTP 状态码 |
| raw_payload | text/json | 原始采集结果 |
| error_message | varchar(512) | 采集失败原因 |
| source_type | varchar(32) | local/push/agent/scheduled |
|
这样后面可以更清楚地区分：
- 本机采集产生的快照
- 外部上报产生的快照
- 调度任务自动采集产生的快照

---

### 5.5 状态配置审计表

#### `system_status_audit`

记录关键配置变更。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键 |
| system_id | bigint | 系统 ID |
| target_id | bigint | 目标 ID，可空 |
| action | varchar(64) | 操作类型 |
| operator_user_id | bigint | 操作人 |
| before_json | text/json | 变更前 |
| after_json | text/json | 变更后 |
| created_at | datetime | 操作时间 |

---

## 6. 管理端页面设计建议

### 6.1 页面一：系统状态总览

#### 目标
- 展示当前用户可见系统的状态汇总
- 支持按环境、状态颜色筛选
- 支持查看异常系统

#### 字段建议
- 系统名称
- 系统编码
- 环境
- 当前状态颜色
- 最后采集时间
- CPU / MEM / DISK
- 端口状态
- HTTP 状态
- 最近巡检结果
- 最近自检结果

#### 注意
这里的数据范围应来自：
- 当前登录用户可见的 `user_system_roles`

而不是直接 `System.all()`。

---

### 6.2 页面二：系统状态配置

#### 目标
配置某个系统的状态采集目标。

#### 页面内容
- 基本信息
  - 系统名称
  - 系统编码
  - 环境
- 采集目标列表
  - 目标名称
  - 目标类型
  - 采集方式
  - 主机/IP
  - 端口
  - URL
  - 是否启用
  - 权重
- 操作
  - 新增目标
  - 编辑目标
  - 禁用目标
  - 删除目标（谨慎）
  - 手动触发采集

---

### 6.3 页面三：状态规则配置

#### 目标
配置状态阈值与判定规则。

#### 页面内容
- 规则范围：全局 / 系统 / 目标
- CPU 告警 / 严重阈值
- 内存告警 / 严重阈值
- 磁盘告警 / 严重阈值
- HTTP 响应时间告警 / 严重阈值
- 连续失败次数阈值
- 启用状态

---

### 6.4 页面四：用户可见范围配置

#### 目标
配置某个用户能看哪些系统，能做什么操作。

#### 页面内容
- 用户列表 / 用户详情
- 已授权系统列表
- 每个系统下的权限开关：
  - 可查看状态
  - 可查看日志
  - 可触发采集
  - 可管理状态配置
- 批量授权 / 批量撤销

---

### 6.5 页面五：采集记录与审计

#### 目标
查看系统状态采集历史与配置变更历史。

#### 页面内容
- 最近采集记录
  - 系统
  - 目标
  - 采集方式
  - 状态结果
  - 失败原因
  - 采集时间
- 配置审计记录
  - 操作人
  - 修改字段
  - 修改前后差异
  - 操作时间

---

## 7. 后端接口演进建议

### 7.1 查询总览

#### 当前
- `GET /monitoring/overview`
- `GET /systems/status/overview`

#### 建议
统一为更清晰的体系，例如：

- `GET /status/overview`
- `GET /status/systems/{system_id}`
- `GET /status/systems/{system_id}/targets`
- `GET /status/systems/{system_id}/snapshots`

并在接口内部按 `user_system_roles` 做可见范围过滤。

---

### 7.2 配置采集目标

建议新增：

- `GET /status/config/systems/{system_id}/targets`
- `POST /status/config/systems/{system_id}/targets`
- `PUT /status/config/targets/{target_id}`
- `DELETE /status/config/targets/{target_id}`

---

### 7.3 配置规则

建议新增：

- `GET /status/config/rules`
- `POST /status/config/rules`
- `PUT /status/config/rules/{rule_id}`

---

### 7.4 手动触发采集

建议新增：

- `POST /status/collect/systems/{system_id}`
- `POST /status/collect/targets/{target_id}`

后续可按 collector_type 分发不同采集器。

---

### 7.5 外部上报

保留现有思路，但建议后续增强：

- `POST /status/push/systems/{system_id}`
- `POST /status/push/targets/{target_id}`

并支持：
- token 鉴权
- source 标识
- trace / request_id

---

## 8. 状态汇总规则建议

一个系统可能有多个 target，需要定义聚合规则。

### 建议聚合优先级

1. 任一关键 target = red → 系统 red
2. 无 red，但存在 warning/yellow → 系统 yellow
3. 全部 normal → 系统 green
4. 全部 unknown → 系统 unknown / gray

### 建议支持 target 权重

某些 target 比其他 target 更关键，例如：
- 后端 API 健康检查权重高
- 单个非核心端口权重低

后续可在 `system_status_targets.weight` 中配置。

---

## 9. 与日志权限设计的衔接

建议“系统状态”和“日志分析”统一走同一套系统可见范围模型。

即：
- 先由 `user_system_roles` 决定用户可见哪些系统
- 再由各自模块细分：
  - `can_view_status`
  - `can_view_logs`
  - `can_manage_status_config`

这样可以避免：
- 用户能看状态但不能看日志
- 或用户能看日志但不该看到该系统状态

配置模型会更清晰。

---

## 10. 分阶段落地建议

### 第一阶段（最小可用）

目标：先把“可见范围 + 配置入口”补上。

建议先做：
1. 新增 `user_system_roles`
2. overview 接口按用户系统范围过滤
3. 管理端增加“用户可见系统配置”页面
4. 管理端增加“系统状态目标配置”页面
5. 支持 `local / tcp / http / push` 四种 target

### 第二阶段（增强）

目标：让状态采集更像真正的运维能力。

建议再做：
1. 按 target 配置状态规则
2. 支持定时采集任务
3. 支持采集失败告警
4. 支持查看快照历史曲线
5. 支持采集结果审计

### 第三阶段（高级）

目标：支持多宿主机、多节点、远程采集。

建议再做：
1. 支持 SSH 远程采集
2. 支持 Agent 模式上报
3. 支持多实例聚合
4. 支持跨环境状态对比
5. 支持与日志、巡检、自检联动展示

---

## 11. 结论

当前 Aegis 的系统状态能力已经有基础雏形，但仍属于“系统 + 最近状态快照”的早期实现。

后续如果要真正支持“通过管理端配置系统状态”，建议围绕以下主线推进：

1. **先解决用户可见范围**：谁能看哪些系统
2. **再解决状态采集目标配置**：一个系统采哪些状态
3. **再解决规则与汇总**：如何判红黄绿
4. **最后补齐调度、审计、外部上报与多采集器扩展**

这样可以让系统状态模块从“当前宿主机状态展示”逐步演进成“面向多系统、可配置、可授权的统一状态管理能力”。
