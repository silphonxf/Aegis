# Aegis 共享主数据模型草案 v1

> 目标：统一管理端与移动端使用的用户、系统、机房、巡检点、资产、应急处置配置数据模型。管理端负责配置与审阅，移动端负责消费与执行。

## 1. 设计原则

- 管理端不是独立业务端，而是移动端的配置界面与审阅界面
- 系统 / 用户 / 机房 / 巡检点 / 应急处置配置必须共用同一套主数据
- 应急处置配置最终服务于移动端展示与执行
- 当前数据库默认按 MySQL 方案推进

---

## 2. 表处理总览

### 2.1 保留

- `roles`
- `system_status_snapshots`
- `inspection_records`
- `checklist_templates`
- `selfcheck_records`
- `audit_logs`
- `status_rules`
- `tool_tasks`
- `ai_diagnoses`
- `offline_analysis_tasks`
- `offline_analysis_results`
- `ai_conversations`
- `ai_chat_files`
- `ai_chat_messages`
- `ai_chat_summaries`

### 2.2 保留但改造

- `users`
- `systems`
- `inspection_points`
- `assets`

### 2.3 新增

- `system_user_bindings`
- `rooms`
- `emergency_hosts`
- `runbooks`

---

## 3. 具体表结构草案

## 3.1 `roles`

### 用途
系统角色字典表。

### 字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| code | VARCHAR(32) | 是 | 角色编码，唯一 |
| name | VARCHAR(64) | 是 | 角色名称 |

---

## 3.2 `users`

### 用途
系统登录用户主表。

### 调整原则
- 不新增扩展字段
- 去掉 `nickname`

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| username | VARCHAR(64) | 是 | 登录账号，唯一 |
| avatar_url | VARCHAR(512) | 否 | 头像地址 |
| password_hash | VARCHAR(255) | 是 | 密码哈希 |
| role_id | BIGINT | 是 | 关联 `roles.id` |
| is_active | TINYINT(1) | 是 | 是否启用 |
| created_at | DATETIME | 是 | 创建时间 |

---

## 3.3 `systems`

### 用途
信息系统主表，管理端和移动端都围绕它组织自检、状态、责任人和预案联动。

### 调整原则
- 不再以 `owner_user_id` 作为最终责任人模型
- 改为通过 `system_user_bindings` 维护多人关联

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| system_code | VARCHAR(64) | 是 | 系统编码，唯一 |
| name | VARCHAR(128) | 是 | 系统名称 |
| env | VARCHAR(32) | 是 | 环境，如 prod / test |
| check_frequency | VARCHAR(32) | 否 | 检查频次，如 per_shift / daily / weekly |
| remark | VARCHAR(500) | 否 | 备注 |
| is_active | TINYINT(1) | 是 | 是否启用 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

### 兼容建议
- 现有 `owner_user_id` 可短期保留用于数据迁移
- 最终应从模型与接口层移除直接依赖

---

## 3.4 `system_user_bindings`

### 用途
系统与用户的多对多关联表，用于表达负责人、值班、审阅等角色关系。

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| system_id | BIGINT | 是 | 关联 `systems.id` |
| user_id | BIGINT | 是 | 关联 `users.id` |
| binding_role | VARCHAR(32) | 是 | 关系角色：owner / duty / reviewer |
| is_primary | TINYINT(1) | 是 | 是否主负责人 |
| created_at | DATETIME | 是 | 创建时间 |

### 索引建议
- 唯一索引：`(system_id, user_id, binding_role)`
- 普通索引：`system_id`
- 普通索引：`user_id`

---

## 3.5 `rooms`

### 用途
机房/区域主表，为巡检点、资产、应急主机提供统一位置主数据。

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| room_code | VARCHAR(64) | 是 | 机房/区域编码，唯一 |
| room_name | VARCHAR(128) | 是 | 机房/区域名称 |
| building | VARCHAR(128) | 否 | 所属楼宇 |
| floor | VARCHAR(64) | 否 | 楼层 |
| location_detail | VARCHAR(255) | 否 | 详细位置描述 |
| remark | VARCHAR(500) | 否 | 备注 |
| is_active | TINYINT(1) | 是 | 是否启用 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

---

## 3.6 `inspection_points`

### 用途
巡检点主表，承接二维码/NFC 点位与移动端巡检定位。

### 调整原则
- 从“系统下的字符串 location”升级为真正点位模型
- 通过 `room_id` 归属机房/区域

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| room_id | BIGINT | 是 | 关联 `rooms.id` |
| system_id | BIGINT | 否 | 关联 `systems.id`，可为空 |
| point_code | VARCHAR(64) | 是 | 点位编码 |
| point_name | VARCHAR(128) | 是 | 点位名称 |
| point_type | VARCHAR(32) | 是 | qr / nfc / mixed |
| qr_content | VARCHAR(255) | 否 | 二维码内容 |
| nfc_tag | VARCHAR(255) | 否 | NFC 标签值 |
| location_detail | VARCHAR(255) | 否 | 机房内具体位置 |
| is_active | TINYINT(1) | 是 | 是否启用 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

### 索引建议
- 唯一索引：`point_code`
- 唯一索引：`qr_content`（允许空值时注意实现方式）
- 普通索引：`room_id`
- 普通索引：`system_id`

---

## 3.7 `inspection_records`

### 用途
移动端巡检记录表。

### 保留方向
当前表保留，建议后续补强位置和来源字段。

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| system_id | BIGINT | 是 | 关联 `systems.id` |
| point_id | BIGINT | 是 | 关联 `inspection_points.id` |
| room_id | BIGINT | 否 | 冗余记录巡检时所属机房 |
| inspector_id | BIGINT | 是 | 关联 `users.id` |
| result | VARCHAR(16) | 是 | normal / abnormal |
| note | TEXT | 否 | 备注 |
| source | VARCHAR(32) | 否 | mobile_qr / mobile_nfc / manual |
| inspected_at | DATETIME | 是 | 巡检时间 |

---

## 3.8 `checklist_templates`

### 用途
系统自检模板。

### 建议
当前保留。

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| system_id | BIGINT | 是 | 关联 `systems.id` |
| check_type | VARCHAR(16) | 是 | 自检类型 |
| name | VARCHAR(128) | 是 | 模板名称 |
| is_active | TINYINT(1) | 是 | 是否启用 |

---

## 3.9 `selfcheck_records`

### 用途
移动端自检记录，管理端负责审阅。

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| system_id | BIGINT | 是 | 关联 `systems.id` |
| template_id | BIGINT | 是 | 关联 `checklist_templates.id` |
| operator_id | BIGINT | 是 | 关联 `users.id` |
| result | VARCHAR(16) | 是 | normal / warning / critical |
| summary | TEXT | 否 | 自检说明 |
| review_status | VARCHAR(16) | 否 | pending / reviewed |
| reviewed_by | BIGINT | 否 | 审阅人，关联 `users.id` |
| reviewed_at | DATETIME | 否 | 审阅时间 |
| checked_at | DATETIME | 是 | 自检时间 |

---

## 3.10 `assets`

### 用途
资产/服务器基础数据表，供系统、巡检、应急配置共同引用。

### 调整原则
- 逐步弱化 `location` 字符串
- 用 `room_id` 建立和机房的强关联

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| asset_code | VARCHAR(64) | 是 | 资产编码，唯一 |
| name | VARCHAR(128) | 是 | 资产名称 |
| category | VARCHAR(64) | 是 | 分类，如 server / network / terminal |
| system_id | BIGINT | 否 | 关联 `systems.id` |
| room_id | BIGINT | 否 | 关联 `rooms.id` |
| location | VARCHAR(255) | 否 | 兼容保留字段 |
| ip_address | VARCHAR(64) | 否 | IP 地址 |
| port | INT | 否 | 端口 |
| connection_type | VARCHAR(32) | 否 | ssh / db / agent |
| status | VARCHAR(32) | 是 | 资产状态 |
| remark | VARCHAR(500) | 否 | 备注 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

---

## 3.11 `emergency_hosts`

### 用途
应急执行主机表，替代当前 JSON 配置中的 SSH 主机部分。

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| host_code | VARCHAR(64) | 是 | 主机编码，唯一 |
| host_name | VARCHAR(128) | 是 | 主机名称 |
| host_ip | VARCHAR(120) | 是 | 主机 IP |
| port | INT | 是 | SSH 端口 |
| username | VARCHAR(64) | 是 | 登录账号 |
| auth_type | VARCHAR(32) | 是 | password / private_key |
| password_ciphertext | TEXT | 否 | 加密后的密码 |
| private_key_ciphertext | LONGTEXT | 否 | 加密后的私钥 |
| private_key_passphrase_ciphertext | TEXT | 否 | 私钥口令 |
| connect_timeout_ms | INT | 是 | 连接超时 |
| system_id | BIGINT | 否 | 关联 `systems.id` |
| room_id | BIGINT | 否 | 关联 `rooms.id` |
| asset_id | BIGINT | 否 | 关联 `assets.id` |
| is_active | TINYINT(1) | 是 | 是否启用 |
| remark | VARCHAR(500) | 否 | 备注 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

---

## 3.12 `runbooks`

### 用途
统一承接服务器动作、数据库动作、进程动作等应急预案配置。

### 建议字段
| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| id | BIGINT | 是 | 主键 |
| runbook_code | VARCHAR(64) | 是 | 预案编码，唯一 |
| runbook_name | VARCHAR(128) | 是 | 预案名称 |
| runbook_type | VARCHAR(32) | 是 | server / database / process |
| system_id | BIGINT | 否 | 关联 `systems.id` |
| target_host_id | BIGINT | 否 | 关联 `emergency_hosts.id` |
| script_type | VARCHAR(32) | 是 | shell / sql |
| script_body | LONGTEXT | 是 | 脚本主体 |
| confirm_text | VARCHAR(500) | 否 | 执行确认文案 |
| risk_level | VARCHAR(32) | 否 | low / medium / high |
| enabled | TINYINT(1) | 是 | 是否启用 |
| remark | VARCHAR(500) | 否 | 备注 |
| created_at | DATETIME | 是 | 创建时间 |
| updated_at | DATETIME | 是 | 更新时间 |

---

## 4. 迁移建议顺序

### 第一阶段：先补共享主表
1. 新增 `system_user_bindings`
2. 新增 `rooms`
3. 改造 `inspection_points`
4. 改造 `assets`
5. 改造 `systems`

### 第二阶段：补管理端/移动端共享接口
1. 系统负责人改走关联表
2. 巡检点改走 `room_id + point_id`
3. 资产位置改走 `room_id`

### 第三阶段：应急处置正式入库
1. 新增 `emergency_hosts`
2. 新增 `runbooks`
3. 将 `config/emergency_ops.json` 迁移到数据库

---

## 5. 当前仍待确认的小点

### `systems.check_frequency`
建议值是否固定为：
- `per_shift`
- `daily`
- `weekly`
- `custom`

### `system_user_bindings.binding_role`
当前建议值：
- `owner`
- `duty`
- `reviewer`

### `inspection_points.point_type`
当前建议值：
- `qr`
- `nfc`
- `mixed`

### `runbooks.runbook_type`
当前建议值：
- `server`
- `database`
- `process`

如果这些枚举值不改，就可以直接往模型与 migration 落了。
