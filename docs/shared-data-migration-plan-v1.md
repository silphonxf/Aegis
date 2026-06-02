# Aegis 共享主数据迁移方案 v1

> 基于 `docs/shared-data-model-v1.md` 制定的第一版迁移方案，目标是在尽量少打断现有功能的前提下，把管理端与移动端逐步迁到同一套共享主数据模型上。

## 1. 迁移目标

本轮迁移要解决 4 件事：

1. `users` 去掉 `nickname`
2. `systems` 从单负责人模型过渡到多用户关联模型
3. `inspection_points`、`assets` 从字符串位置字段过渡到 `rooms` 强关联
4. 应急处置配置从 JSON 占位态设计为可正式入库的数据库模型

---

## 2. 总体迁移策略

采用 **三阶段迁移**：

### 阶段 A：先加新表/新字段，不立刻拆旧字段
目标：先让新模型可落地，不立即中断现有接口。

### 阶段 B：补数据迁移与双写/兼容
目标：让旧数据平滑迁到新结构，同时保留短期兼容。

### 阶段 C：清理旧字段和旧配置来源
目标：当管理端/移动端/接口都切到新模型后，再移除旧字段和 JSON 配置依赖。

---

## 3. 迁移对象清单

## 3.1 `users`

### 当前状态
- 保留现有主表
- 当前字段中包含 `nickname`

### 目标状态
- 删除 `nickname`
- 不新增扩展字段

### 迁移动作
#### 阶段 A
- 模型层停止依赖 `nickname`
- 前端/接口不再读写 `nickname`

#### 阶段 B
- 清理代码中所有 `nickname` 相关引用

#### 阶段 C
- Alembic migration 删除 `users.nickname`

### 风险
- 如果前端 profile 页面仍在使用 `nickname`，要先改前端再删字段

---

## 3.2 `systems`

### 当前状态
- 现有 `owner_user_id` 是单负责人模型

### 目标状态
- `systems` 只保留系统主属性
- 负责人/值班/审阅关系改由 `system_user_bindings` 承担
- 新增：`check_frequency`、`remark`、`updated_at`

### 迁移动作
#### 阶段 A
- 给 `systems` 加字段：
  - `check_frequency`
  - `remark`
  - `updated_at`
- 保留 `owner_user_id` 暂不删除
- 新建 `system_user_bindings`

#### 阶段 B
- 将已有 `systems.owner_user_id` 迁移到 `system_user_bindings`
- 迁移规则：
  - `system_id = systems.id`
  - `user_id = owner_user_id`
  - `binding_role = 'owner'`
  - `is_primary = 1`
- 后端查询负责人统一改查 `system_user_bindings`
- 管理端系统编辑页改为多选负责人

#### 阶段 C
- 删除 `owner_user_id`

### 风险
- 当前如果有接口或逻辑直接读 `owner_user_id`，需要先做兼容转换层

---

## 3.3 `system_user_bindings`

### 当前状态
- 不存在

### 目标状态
- 成为系统与用户关系的唯一正式来源

### 初始数据来源
- 来自 `systems.owner_user_id`
- 后续管理端增删改维护

### 建议 migration
- 新建表
- 建唯一索引：`(system_id, user_id, binding_role)`
- 为 `system_id`、`user_id` 加普通索引

---

## 3.4 `rooms`

### 当前状态
- 不存在
- 机房语义散落在：
  - `inspection_points.location`
  - `assets.location`

### 目标状态
- 机房/区域由 `rooms` 统一维护

### 迁移动作
#### 阶段 A
- 新建 `rooms`

#### 阶段 B
- 从现有 `inspection_points.location` 和 `assets.location` 提取去重后的房间名
- 生成基础 `rooms` 数据
- 建议迁移策略：
  1. 优先以 `inspection_points.location` 为主要来源
  2. 再补充 `assets.location` 中尚未覆盖的值
- 自动生成：
  - `room_code`：如 `ROOM_0001`
  - `room_name`：取原 location 文本
  - 其余字段为空或默认值

#### 阶段 C
- 管理端改为维护 `rooms`
- 旧的 location 字符串仅作兼容展示或彻底移除

### 风险
- 现有 location 文本可能不规范，如“机房A”“主机房A区”“A01机柜”混杂
- 第一轮迁移建议先保留原始文本，不做过度自动归并

---

## 3.5 `inspection_points`

### 当前状态
当前字段：
- `system_id`
- `point_code`
- `qr_content`
- `location`

### 目标状态
增加：
- `room_id`
- `point_name`
- `point_type`
- `nfc_tag`
- `location_detail`
- `is_active`
- `created_at`
- `updated_at`

### 迁移动作
#### 阶段 A
- 给 `inspection_points` 新增字段：
  - `room_id`
  - `point_name`
  - `point_type`
  - `nfc_tag`
  - `location_detail`
  - `is_active`
  - `created_at`
  - `updated_at`
- 暂时保留 `location`

#### 阶段 B
- 根据 `location -> rooms.id` 映射回填 `room_id`
- 回填策略：
  - `point_name = location`（若旧数据为空则退化为 `point_code`）
  - `point_type = 'qr'`
  - `location_detail = location`
  - `is_active = 1`
- 移动端解析巡检点逻辑改为优先读取：
  - `point_name`
  - `room_id`
  - `location_detail`

#### 阶段 C
- 删除 `location`

### 风险
- 旧二维码逻辑里可能直接使用 `location` 作为显示文本，需要前端同步切换

---

## 3.6 `inspection_records`

### 当前状态
已存在：
- `system_id`
- `point_id`
- `inspector_id`
- `result`
- `note`
- `inspected_at`

### 目标状态
建议补充：
- `room_id`
- `source`

### 迁移动作
#### 阶段 A
- 新增字段：
  - `room_id`
  - `source`

#### 阶段 B
- 通过 `point_id -> inspection_points.room_id` 回填 `room_id`
- `source` 对历史数据可统一填：`manual_migrated`

#### 阶段 C
- 新记录创建逻辑统一写入 `room_id` 与 `source`

---

## 3.7 `assets`

### 当前状态
当前字段：
- `asset_code`
- `name`
- `category`
- `system_id`
- `location`
- `status`
- `created_at`

### 目标状态
新增：
- `room_id`
- `ip_address`
- `port`
- `connection_type`
- `remark`
- `updated_at`

### 迁移动作
#### 阶段 A
- 给 `assets` 新增字段：
  - `room_id`
  - `ip_address`
  - `port`
  - `connection_type`
  - `remark`
  - `updated_at`
- 保留 `location`

#### 阶段 B
- 根据 `location -> rooms.id` 回填 `room_id`
- 管理端资产录入从“位置字符串”切换成“机房下拉 + 位置备注”

#### 阶段 C
- `location` 只作为兼容展示字段，最终视情况删除

### 风险
- 资产位置可能比机房更细，例如“机房A-01机柜”，后续应拆成：
  - `room_id = 机房A`
  - `location` 或 `remark = 01机柜`

---

## 3.8 `selfcheck_records`

### 当前状态
可记录自检结果，但缺少审阅状态

### 目标状态
新增：
- `review_status`
- `reviewed_by`
- `reviewed_at`

### 迁移动作
#### 阶段 A
- 新增上述字段

#### 阶段 B
- 历史数据默认：
  - `review_status = NULL` 或 `pending`

#### 阶段 C
- 管理端审阅页接入正式字段

---

## 3.9 `emergency_hosts`

### 当前状态
- 不存在数据库表
- 当前使用 `config/emergency_ops.json`

### 目标状态
- SSH 主机配置正式入库

### 迁移动作
#### 阶段 A
- 新建 `emergency_hosts`

#### 阶段 B
- 编写一次性脚本，将 `emergency_ops.json` 中 `ssh_hosts` 导入数据库

#### 阶段 C
- 管理端改为只读写数据库
- 后端服务停止读取 JSON 作为主来源

---

## 3.10 `runbooks`

### 当前状态
- 不存在数据库表
- 当前服务器动作、数据库动作、进程动作都在 JSON 中分散维护

### 目标状态
- 统一入 `runbooks`

### 迁移动作
#### 阶段 A
- 新建 `runbooks`

#### 阶段 B
- 将 JSON 中：
  - `server_actions`
  - `database_actions`
  - `process_actions`
 统一转换导入 `runbooks`
- 映射建议：
  - `server_actions` -> `runbook_type = 'server'`
  - `database_actions` -> `runbook_type = 'database'`
  - `process_actions` -> `runbook_type = 'process'`

#### 阶段 C
- 移动端应急处置改为直接消费数据库配置
- JSON 改为废弃

---

## 4. 迁移映射表

## 4.1 `systems.owner_user_id` -> `system_user_bindings`

| 旧来源 | 新目标 | 映射规则 |
|---|---|---|
| systems.id | system_user_bindings.system_id | 直接映射 |
| systems.owner_user_id | system_user_bindings.user_id | 非空时迁移 |
| 常量 | system_user_bindings.binding_role | `'owner'` |
| 常量 | system_user_bindings.is_primary | `1` |

---

## 4.2 `inspection_points.location` -> `rooms` + `inspection_points.room_id`

| 旧来源 | 新目标 | 映射规则 |
|---|---|---|
| inspection_points.location | rooms.room_name | 去重后生成 |
| 自动生成 | rooms.room_code | `ROOM_0001` 递增 |
| inspection_points.location | inspection_points.point_name | 为空时退化为 `point_code` |
| inspection_points.location | inspection_points.location_detail | 原样保留 |
| location 匹配结果 | inspection_points.room_id | 按 room_name 回填 |

---

## 4.3 `assets.location` -> `rooms` + `assets.room_id`

| 旧来源 | 新目标 | 映射规则 |
|---|---|---|
| assets.location | rooms.room_name | 若未存在则补建 |
| location 匹配结果 | assets.room_id | 按 room_name 回填 |
| assets.location | assets.location | 原字段短期保留 |

---

## 4.4 `emergency_ops.json` -> `emergency_hosts` / `runbooks`

| JSON 节点 | 新表 | 映射说明 |
|---|---|---|
| ssh_hosts | emergency_hosts | 一条主机配置一条记录 |
| server_actions | runbooks | `runbook_type='server'` |
| database_actions | runbooks | `runbook_type='database'` |
| process_actions | runbooks | `runbook_type='process'` |

---

## 5. 建议的 Alembic 拆分顺序

建议拆成 4 个 migration，而不是一次大迁移：

### Migration 1：共享主表补齐
- 新建 `system_user_bindings`
- 新建 `rooms`
- `systems` 加字段
- `inspection_points` 加字段
- `inspection_records` 加字段
- `assets` 加字段
- `selfcheck_records` 加字段

### Migration 2：数据回填
- 从 `owner_user_id` 迁移到 `system_user_bindings`
- 从 `inspection_points.location` / `assets.location` 生成 `rooms`
- 回填 `inspection_points.room_id`
- 回填 `assets.room_id`
- 回填 `inspection_records.room_id`

### Migration 3：应急处置入库
- 新建 `emergency_hosts`
- 新建 `runbooks`
- 预留 JSON -> DB 导入脚本执行窗口

### Migration 4：旧字段清理
- 删除 `users.nickname`
- 删除 `systems.owner_user_id`
- 删除 `inspection_points.location`
- 视情况删除或保留 `assets.location`

---

## 6. 我建议的实现顺序

如果要开始真正动代码，我建议按下面顺序最稳：

1. 先做 migration 1（只加不删）
2. 改 models / schemas / API 兼容新字段
3. 做 migration 2（回填数据）
4. 改管理端 / 移动端接口消费
5. 做 emergency JSON 入库
6. 最后再删旧字段

---

## 7. 当前结论

当前最适合马上进入开发的是：

### 第一批落地
- `system_user_bindings`
- `rooms`
- `systems` 扩字段
- `inspection_points` 扩字段
- `assets` 扩字段
- `inspection_records` 扩字段
- `selfcheck_records` 扩字段

### 第二批落地
- `emergency_hosts`
- `runbooks`
- JSON 导入脚本

### 最后清理
- `users.nickname`
- `systems.owner_user_id`
- `inspection_points.location`
- `assets.location`（视兼容情况决定）
