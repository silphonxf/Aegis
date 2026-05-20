# Aegis 日志可见范围与管理端配置设计（初稿）

> 目标：为后续“谁能看哪些系统、哪些日志文件、哪些日志级别”建立可扩展的权限与配置模型。当前先形成设计文档，后续在管理端优化阶段落地。

## 1. 背景

Aegis 现在已经有：
- 用户
- 角色
- 系统
- 日志分析入口
- 基础 RBAC

但日志分析目前仍偏“工具型入口”：
- 用户手动选择日志来源
- 手动选择日志文件
- 后端按参数读取日志

这能满足当前联调，但还不满足正式场景里的权限收敛要求。

你现在提出的方向很关键：

**用户 - 系统 - 角色 - 日志**

也就是说，后续日志可见范围不能只看“用户是什么全局角色”，而要看：
- 这个用户对哪些系统有关系
- 在每个系统上扮演什么角色
- 该角色能看哪些日志来源/日志文件/日志级别
- 这些规则由管理端配置维护

这个方向本质上是：

**从全局 RBAC，升级为“按系统维度约束的日志访问控制模型”。**

---

## 2. 设计目标

后续日志访问控制需要满足：

1. **按系统收敛可见范围**
   - 用户不能默认看到所有系统日志
   - 只能看到被授权系统的日志

2. **按角色收敛可见范围**
   - 同一系统下，不同角色可见范围不同
   - 例如巡检员只能看巡检相关日志，系统管理员可看后端应用日志，超级管理员可看全局

3. **按日志对象收敛可见范围**
   - 可限制到日志来源（system / aegis）
   - 可限制到日志文件名（backend.log / syslog / frontend-mobile.log）
   - 可限制到日志级别（info / warning / error）

4. **由管理端维护，不写死在代码里**
   - 用户与系统的关系要可配置
   - 日志授权规则要可配置
   - 后续新增日志文件时，不应需要改一堆前端逻辑

5. **兼顾当前实现可平滑演进**
   - 现在的日志分析页、日志读取接口尽量少推翻
   - 优先在后端权限层和管理端配置层演进

---

## 3. 核心设计思路

建议把后续模型拆成 4 层：

1. **用户（User）**
2. **系统（System）**
3. **用户-系统角色关系（UserSystemRole）**
4. **日志访问规则（LogAccessPolicy）**

即：

- 先确定一个用户和哪些系统有关系
- 再确定该用户在这个系统上是什么角色
- 再由该角色匹配日志访问策略
- 最终决定这个用户能看到哪些日志

---

## 4. 建议的数据模型

### 4.1 users（已有）
继续保留当前用户表。

核心字段：
- `id`
- `username`
- `password_hash`
- `is_active`

说明：
- 用户仍然保留“平台登录身份”
- 但日志访问不再只靠全局 role_id 判断

---

### 4.2 roles（已有，可继续保留）
继续保留当前角色表，用于平台级基础权限。

建议仍保留：
- `inspector`
- `admin`
- `super_admin`

说明：
- 平台级角色决定“能不能进入某些功能模块”
- 系统级角色决定“进入后能看哪个系统的哪些日志”

也就是说，后续会形成：
- **平台角色**：控制菜单与功能入口
- **系统角色**：控制某个系统维度的数据访问范围

---

### 4.3 systems（已有）
继续保留被管系统表。

建议补强字段：
- `id`
- `system_code`
- `name`
- `env`
- `is_active`
- `owner_user_id`（已有/可选）

说明：
- 日志权限最终应围绕 `system_id` 做收敛

---

### 4.4 user_system_roles（新增，关键）
表示：**某个用户在某个系统上扮演什么角色**。

建议字段：
- `id`
- `user_id`
- `system_id`
- `role_code`
- `enabled`
- `created_at`
- `updated_at`
- `remark`

示例：
- 用户 A 在“航班调度系统”上是 `admin`
- 用户 A 在“离港系统”上只是 `inspector`
- 用户 B 在“航班调度系统”上是 `viewer`（后续可扩展）

说明：
- 这是后续日志访问控制最核心的桥表
- 一个用户可以对应多个系统
- 一个系统可以有多个用户
- 每条关系都可以有不同的角色

---

### 4.5 log_sources（新增，可选配置表）
用于维护日志来源分类。

建议字段：
- `id`
- `source_code`：如 `aegis` / `system`
- `source_name`
- `enabled`
- `remark`

说明：
- 便于后续管理端统一维护来源字典
- 也利于以后扩展更多来源，例如：
  - `nginx`
  - `dm`
  - `docker`
  - `openclaw`

---

### 4.6 log_files（新增，关键配置表）
用于维护“某个系统有哪些日志文件可供查看”。

建议字段：
- `id`
- `system_id`（可为空，若是全局日志）
- `source_code`
- `file_code`
- `file_name`
- `file_path`
- `file_kind`（backend / frontend / system / middleware）
- `min_level_default`（默认最小日志级别）
- `enabled`
- `remark`

示例：
- `backend.log`
- `backend-https.log`
- `frontend-mobile.log`
- `/var/log/syslog`

说明：
- 后续前端下拉不应该写死候选项
- 应改为从这里下发
- 这样管理端新增一个日志文件后，移动端可以直接感知

---

### 4.7 log_access_policies（新增，关键权限表）
用于配置：**某类角色在某类系统或具体系统上，允许看哪些日志**。

建议字段：
- `id`
- `role_code`
- `system_id`（可选，为空表示对所有系统同类角色生效）
- `source_code`
- `file_code` 或 `log_file_id`
- `allow_levels`（如 `info,warning,error`）
- `allow_keywords`（可选）
- `deny_keywords`（可选）
- `time_range_limit_hours`（可选，例如只能看最近 24 小时）
- `enabled`
- `remark`

说明：
- 这是“日志可见范围”的规则表
- 它不直接绑定某个用户，而是绑定“系统角色”
- 用户真正看到什么，由：
  - `user_system_roles`
  - `log_access_policies`
  联合决定

---

## 5. 权限判断链路

建议后续日志读取接口按下面顺序判断：

### Step 1：识别当前用户
获取当前登录用户 `current_user`

### Step 2：识别当前用户要查看哪个系统
前端日志分析页后续应显式带上：
- `system_id`

说明：
- 没有 `system_id` 的日志读取请求，后续不应直接放行
- 除非是超级管理员查看平台级全局日志

### Step 3：查用户在该系统上的角色
到 `user_system_roles` 里查询：
- `user_id`
- `system_id`
- `enabled = true`

若查不到：
- 拒绝访问

### Step 4：查该角色可用的日志访问策略
到 `log_access_policies` 里查：
- `role_code`
- `system_id` 或通用规则
- `source_code`
- `file_code`

若策略不允许：
- 拒绝访问

### Step 5：按策略裁剪请求参数
即使前端传了：
- `level=info`
- `start_at=过去7天`

也要被策略层二次裁剪：
- 若策略只允许 `warning/error`，则不能降到 `info`
- 若策略最多允许最近 24h，则不能查 7 天

### Step 6：真正读取日志
通过已经存在的日志读取逻辑：
- 读取指定文件
- 按时间范围筛选
- 按级别筛选
- 返回结果

---

## 6. 管理端建议改造方向

后续管理端优化时，建议新增一个“日志权限配置”模块。

### 6.1 菜单建议
新增一级或二级菜单：
- `日志权限配置`

下分 4 个页面：
1. **系统用户角色配置**
2. **日志文件配置**
3. **日志访问策略配置**
4. **日志授权预览 / 生效校验**

---

### 6.2 系统用户角色配置页
用于维护：
- 某个用户对某个系统是什么角色

页面字段建议：
- 用户
- 系统
- 角色
- 启用状态
- 备注

支持：
- 新增
- 编辑
- 禁用
- 按系统查看所有已授权用户

---

### 6.3 日志文件配置页
用于维护系统与日志文件的映射。

字段建议：
- 系统
- 日志来源
- 日志文件名
- 实际文件路径
- 日志类型
- 默认最小级别
- 启用状态

支持：
- 配置某个系统有哪些后端日志/前端日志/系统日志
- 可配置不同环境（prod/test）对应不同路径

---

### 6.4 日志访问策略配置页
用于维护角色到日志范围的映射。

字段建议：
- 系统（可选）
- 角色
- 日志来源
- 日志文件
- 可看级别
- 最大可查时间范围
- 启用状态
- 备注

示例：
- `inspector`：只能看 `backend.log` 的 `warning/error`，时间范围最多 24h
- `admin`：可看 `backend.log + frontend-mobile.log` 的 `info/warning/error`，时间范围最多 72h
- `super_admin`：可看全系统所有文件

---

### 6.5 授权预览 / 生效校验页
这个页我很建议做。

输入：
- 用户
- 系统

输出：
- 当前系统角色
- 可见日志来源
- 可见日志文件
- 可见日志级别
- 最大时间范围

价值：
- 管理员能直接验证配置是否正确
- 降低“为什么这个用户看不到日志”的排障成本

---

## 7. 前端日志分析页后续改造建议

当前日志分析页是“用户自己选来源/文件/时间范围/级别”。

后续接入权限模型后，建议改成：

### 7.1 增加“系统”前置选择
流程建议：
1. 用户先选系统
2. 前端请求后端获取当前用户对该系统的可见日志范围
3. 再动态渲染：
   - 日志来源下拉
   - 日志文件下拉
   - 允许的日志级别
   - 最大时间范围

### 7.2 不再展示超出权限的候选项
例如用户只能看：
- `backend.log`
- `warning/error`

那么前端就不应该显示：
- `syslog`
- `info`

### 7.3 时间范围要受后端规则限制
比如策略只允许最近 24h：
- 快捷按钮只能显示 1h / 3h / 6h / 24h
- 日历选择器也不能选超限时间

---

## 8. 接口演进建议

### 当前接口
目前日志读取接口大致是：

- `GET /api/v1/toolbox/error-logs`

参数：
- `source`
- `file_name`
- `quick_range`
- `start_at`
- `end_at`
- `level`

### 后续建议新增

#### 8.1 查询当前系统日志权限范围
例如：
- `GET /api/v1/log-access/scope?system_id=123`

返回：
```json
{
  "system_id": 123,
  "role_code": "admin",
  "available_sources": ["aegis", "system"],
  "available_files": [
    {"file_name": "backend.log", "source": "aegis"},
    {"file_name": "frontend-mobile.log", "source": "aegis"}
  ],
  "available_levels": ["info", "warning", "error"],
  "max_time_range_hours": 72
}
```

#### 8.2 日志读取接口增加 system_id
例如：
- `GET /api/v1/toolbox/error-logs?system_id=123&source=aegis&file_name=backend.log...`

说明：
- 后端必须基于 `system_id` 做权限校验

---

## 9. 推荐的阶段性落地顺序

### Phase A：先保留当前功能，补设计
当前阶段先保持现状可用：
- 来源选择
- 文件选择
- 时间范围
- 日志级别

这一步你已经明确：
**先不继续改 available_files 动态化，后面再做。**

### Phase B：补系统维度
后续先给日志分析页增加：
- 系统选择

后端日志接口增加：
- `system_id`

### Phase C：落 user_system_roles
实现：
- 用户在某系统上的角色关系表

### Phase D：落 log_files / log_access_policies
实现：
- 日志文件配置
- 日志访问策略配置

### Phase E：管理端页面落地
实现：
- 用户-系统角色配置页
- 日志文件配置页
- 日志权限策略页
- 权限预览页

---

## 10. 当前推荐结论

如果按你现在的思路，我建议最终采用：

### 一句话原则
**日志可见范围 = 用户在某系统上的角色 + 管理端配置的日志访问策略**

### 不建议的做法
不建议继续长期沿用：
- 仅按全局角色决定所有日志权限
- 前端写死日志文件候选
- 用户自己随便选择任何系统日志文件

### 推荐做法
推荐后续演进为：
- 用户先选系统
- 后端判断该用户在该系统上的角色
- 再下发该用户可见的日志范围
- 前端仅展示允许查看的范围

---

## 11. 对当前代码的兼容性评价

这个设计和你现在 Aegis 的代码方向是兼容的。

原因：
- 你已经有 `users / roles / systems`
- 日志分析入口已经存在
- 日志读取接口已经支持来源、文件、时间、级别筛选
- 管理端也已经开始有“配置型能力”的设计思路

所以后续不是推翻重做，而是：

**在现有日志工具链上，往“系统维度授权 + 管理端配置化”方向继续收敛。**

---

## 12. ER 表结构草案（建议 v1）

这一节给出一个尽量兼容当前 Aegis 的数据库设计草案，方便后面真正落表时直接参考。

---

### 12.1 user_system_roles

用途：维护“某个用户在某个系统上是什么角色”。

建议字段：

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | BIGINT | 主键 |
| user_id | BIGINT | 关联 users.id |
| system_id | BIGINT | 关联 systems.id |
| role_code | VARCHAR(32) | 系统维度角色，如 inspector/admin/viewer |
| enabled | BOOLEAN | 是否启用 |
| remark | VARCHAR(255) | 备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

建议约束：
- `UNIQUE(user_id, system_id)`
- `FOREIGN KEY (user_id) REFERENCES users(id)`
- `FOREIGN KEY (system_id) REFERENCES systems(id)`

建议索引：
- `idx_usr_system_role_user(user_id)`
- `idx_usr_system_role_system(system_id)`
- `idx_usr_system_role_role(role_code)`

说明：
- 一个用户在同一个系统上通常只有一个生效角色
- 如果后续需要更复杂授权，也可以再扩展多角色模型，但 v1 先保持简单

---

### 12.2 log_sources

用途：日志来源字典。

建议字段：

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | BIGINT | 主键 |
| source_code | VARCHAR(32) | 唯一编码，如 aegis/system |
| source_name | VARCHAR(64) | 展示名称 |
| enabled | BOOLEAN | 是否启用 |
| remark | VARCHAR(255) | 备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

建议约束：
- `UNIQUE(source_code)`

建议初始值：
- `aegis`
- `system`

后续可扩展：
- `nginx`
- `docker`
- `dm`
- `openclaw`

---

### 12.3 log_files

用途：维护“系统有哪些日志文件可供查看”。

建议字段：

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | BIGINT | 主键 |
| system_id | BIGINT | 关联 systems.id，可为空（全局日志） |
| source_code | VARCHAR(32) | 关联 log_sources.source_code |
| file_code | VARCHAR(64) | 文件唯一编码 |
| file_name | VARCHAR(128) | 展示文件名 |
| file_path | VARCHAR(512) | 实际文件路径 |
| file_kind | VARCHAR(32) | backend/frontend/system/middleware |
| default_level | VARCHAR(16) | 默认日志级别 |
| enabled | BOOLEAN | 是否启用 |
| remark | VARCHAR(255) | 备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

建议约束：
- `UNIQUE(file_code)`
- `FOREIGN KEY (system_id) REFERENCES systems(id)`

建议索引：
- `idx_log_files_system(system_id)`
- `idx_log_files_source(source_code)`
- `idx_log_files_enabled(enabled)`

说明：
- `system_id` 为空时，表示平台级/主机级公共日志
- `file_code` 不建议直接等于 `file_name`，后续便于改名不影响授权引用

示例：
- `aegis_backend_main`
- `aegis_backend_https`
- `aegis_mobile_static`
- `linux_syslog`

---

### 12.4 log_access_policies

用途：维护“某角色在某系统下能看哪些日志”。

建议字段：

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | BIGINT | 主键 |
| role_code | VARCHAR(32) | 系统维度角色 |
| system_id | BIGINT | 可为空，为空表示通用策略 |
| log_file_id | BIGINT | 关联 log_files.id |
| allow_info | BOOLEAN | 是否允许 info |
| allow_warning | BOOLEAN | 是否允许 warning |
| allow_error | BOOLEAN | 是否允许 error |
| max_time_range_hours | INT | 最大可查时间范围 |
| enabled | BOOLEAN | 是否启用 |
| remark | VARCHAR(255) | 备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

建议约束：
- `FOREIGN KEY (system_id) REFERENCES systems(id)`
- `FOREIGN KEY (log_file_id) REFERENCES log_files(id)`

建议索引：
- `idx_log_policy_role(role_code)`
- `idx_log_policy_system(system_id)`
- `idx_log_policy_file(log_file_id)`

说明：
- v1 建议先用三个布尔字段表示级别权限，简单直接
- 后续如果日志级别增多，再演进成 JSON / 多选枚举表

---

### 12.5 log_access_audit（可选）

用途：记录“谁在什么时候查看了哪些日志”，属于日志访问审计。

建议字段：

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | BIGINT | 主键 |
| user_id | BIGINT | 查看者 |
| username | VARCHAR(64) | 冗余用户名 |
| system_id | BIGINT | 查看的系统 |
| source_code | VARCHAR(32) | 日志来源 |
| file_name | VARCHAR(128) | 查看的日志文件 |
| level | VARCHAR(16) | 查询级别 |
| start_at | TIMESTAMP | 查询开始时间 |
| end_at | TIMESTAMP | 查询结束时间 |
| line_count | INT | 返回行数 |
| request_id | VARCHAR(64) | 请求ID |
| created_at | TIMESTAMP | 查询时间 |

建议用途：
- 后续安全审计
- 排查“谁看过哪些敏感日志”
- 做操作留痕

---

### 12.6 与现有表的关系

建议关系如下：

- `users 1:N user_system_roles`
- `systems 1:N user_system_roles`
- `systems 1:N log_files`
- `log_sources 1:N log_files`
- `log_files 1:N log_access_policies`
- `systems 1:N log_access_policies`（可为空表示通用策略）

完整判断链路：

1. 用户登录后拿到 `user_id`
2. 选择系统，得到 `system_id`
3. 到 `user_system_roles` 查该用户在该系统上的 `role_code`
4. 到 `log_access_policies` 查该角色在该系统下可访问的 `log_file_id`
5. 再从 `log_files` 解析出实际可读文件清单

---

### 12.7 推荐的最小落表顺序

如果后面真的开始建表，我建议顺序是：

1. `user_system_roles`
2. `log_sources`
3. `log_files`
4. `log_access_policies`
5. `log_access_audit`（可放后）

原因：
- 前 4 张表就足够形成完整授权闭环
- `log_access_audit` 是增强项，不必卡前期进度

---

## 13. 下一步建议

后续真正开始改管理端时，建议按下面顺序推进：

1. 先补 ER 草图：`user_system_roles / log_files / log_access_policies`
2. 再补管理端菜单与页面草图
3. 再改日志读取接口加入 `system_id`
4. 最后再让前端日志分析页改成“按系统动态受限展示”

这会比较稳，也不容易返工。
