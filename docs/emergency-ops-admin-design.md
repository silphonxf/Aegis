# 应急处置：管理端配置设计（初稿）

> 目标：为移动端“应急处置”提供统一的管理端配置入口，按 **服务器 / 数据库 / 进程** 三个模块维护可执行动作，并通过 SSH / SQL / 脚本模板完成实际执行。

## 1. 管理端菜单建议

新增一级或二级菜单：`应急处置配置`

下分 4 个配置页：
1. **SSH 主机配置**
2. **服务器动作配置**
3. **数据库动作配置**
4. **进程动作配置**

这样做的原因：
- SSH 连接信息和动作定义解耦
- 同一台主机可复用到服务器重启、进程管理、数据库脚本执行
- 后续扩展新动作时不需要重复录入连接信息

---

## 2. SSH 主机配置

用于维护远程服务器连接信息。

### 字段建议
- `host_code`：主机编码（唯一）
- `host_name`：主机名（移动端展示）
- `host_ip`：IP 地址（移动端展示）
- `port`：SSH 端口（默认 22）
- `username`：SSH 用户名
- `auth_type`：认证方式
  - password
  - private_key
- `password_ciphertext`：加密后的密码（若 auth_type=password）
- `private_key_ciphertext`：加密后的私钥（若 auth_type=private_key）
- `private_key_passphrase_ciphertext`：加密后的私钥口令（可选）
- `connect_timeout_ms`
- `enabled`
- `remark`

### 加密要求
SSH 敏感字段 **不能明文存库**：
- SSH 密码
- 私钥
- 私钥口令

建议：
- 使用服务端统一加密函数加密后落库
- 加密主密钥从环境变量读取，不进代码仓库
- 管理端编辑时默认不回显原文，只支持“覆盖更新”

建议环境变量名：
- `AEGIS_SECRET_KEY`
- 或单独拆分：`AEGIS_CREDENTIALS_MASTER_KEY`

---

## 3. 服务器动作配置

对应移动端“服务器操作”。

### 当前目标功能
- 服务器列表：主机名、IP、重启按钮

### 配置模型建议
每条记录代表一个“服务器动作入口”：
- `action_code`：唯一编码
- `action_name`：动作名称（如：服务器重启）
- `target_host_code`：关联 SSH 主机
- `module_type`：server
- `script_type`：shell
- `script_body`：脚本内容 / 命令模板
- `confirm_text`：执行确认文案
- `enabled`
- `remark`

### 当前推荐实现方式
对“服务器重启”来说，可简单约定：
- 管理端配置一个重启脚本模板
- 前端只按主机展示列表
- 点击重启后，后端按 `host_code + action_code` 找到脚本并执行

---

## 4. 数据库动作配置

对应移动端“数据库操作”。

### 当前目标功能
- FOC 密码查询
- FOC 死锁处理
- FOC 数据库闪回
- 数据库表空间

### 配置模型建议
- `action_code`
- `action_name`
- `module_type`：database
- `db_type`：oracle / dameng / mysql / shell_proxy 等
- `target_host_code`：可选（若通过远程 SSH 执行数据库命令）
- `script_type`：sql / shell
- `script_body`
- `param_schema`：JSON，定义输入参数
- `result_mode`：text
- `enabled`
- `remark`

### FOC 密码查询特殊说明
这个功能需要支持参数：
- `system_code`
- `employee_id`

因此脚本模板建议支持占位符，例如：
- `{{system_code}}`
- `{{employee_id}}`

后端执行时做安全替换，不允许直接字符串拼接成高风险 SQL。

### 结果返回
用户已确认：
- 返回 **简单弹窗文本** 即可

所以前端无需复杂富文本，只要后端返回一段文本。

---

## 5. 进程动作配置

对应移动端“进程操作”。

### 当前目标功能
- 进程列表：进程名、进程 ID、重启按钮、关闭按钮

### 配置模型建议
- `action_code`
- `action_name`（如：进程重启 / 进程关闭）
- `module_type`：process
- `target_host_code`
- `process_name`
- `process_id_source`：
  - fixed
  - runtime_detect
- `default_process_id`：可选
- `script_type`：shell
- `script_body`
- `enabled`
- `remark`

### 说明
如果后续进程 ID 是动态的，推荐：
- 展示层用“配置的进程名”
- 执行前由脚本动态查 PID
- 不要强依赖前端传来的 PID 直接 kill

这样更安全，避免误杀。

---

## 6. 配置文件落地建议

如果你希望“后端通过配置文件实现”，推荐先支持一份统一配置文件，再逐步演进到数据库维护。

例如：`backend/config/emergency_ops.yaml`

结构示意：

```yaml
ssh_hosts:
  - host_code: foc-app-01
    host_name: 航信应用服务器-01
    host_ip: 10.10.1.21
    port: 22
    username: ops
    auth_type: password
    password_ciphertext: ENC(...)
    enabled: true

server_actions:
  - action_code: reboot-server
    action_name: 服务器重启
    target_host_code: foc-app-01
    script_type: shell
    script_body: sudo systemctl reboot
    enabled: true

database_actions:
  - action_code: foc-password-query
    action_name: FOC 密码查询
    script_type: sql
    target_host_code: foc-db-01
    param_schema:
      - name: system_code
      - name: employee_id
    script_body: |
      SELECT ...
      WHERE system_code='{{system_code}}'
        AND employee_id='{{employee_id}}';
    enabled: true

process_actions:
  - action_code: restart-foc-gateway
    action_name: 重启 foc-gateway
    target_host_code: foc-app-01
    process_name: foc-gateway
    script_type: shell
    script_body: systemctl restart foc-gateway
    enabled: true
```

---

## 7. 安全与加密注意点

这是这块里最需要认真处理的地方。

### 必须做
1. **SSH 密码 / 私钥加密存储**
2. **主密钥放环境变量，不入库、不进仓库**
3. **管理端敏感字段不回显**
4. **执行日志脱敏**
   - 不记录明文密码
   - 不记录完整私钥
5. **高危动作二次确认**
   - 服务器重启
   - 进程关闭
   - 数据库闪回
6. **权限控制**
   - 仅 `super_admin` 可配置和执行高危应急动作

### 推荐做
1. 为脚本执行做白名单模型，不允许任意输入整段命令直接执行
2. 对模板参数做校验（例如工号、系统编码）
3. 对执行结果做审计日志记录：谁、何时、对哪台主机、执行了哪个动作
4. 对数据库类动作设置超时和输出长度限制

---

## 8. 推荐下一步落地顺序

### 第一步
先做管理端的**配置页面骨架**：
- SSH 主机配置
- 服务器动作配置
- 数据库动作配置
- 进程动作配置

### 第二步
后端先支持：
- 读取配置文件
- 返回移动端展示列表
- 执行 mock 命令链路

### 第三步
再接真实执行：
- SSH 执行
- SQL / shell 模板执行
- 审计与脱敏日志

---

## 9. 当前已确认的产品口径

### 移动端服务器列表
- 主机名
- IP
- 重启按钮

### 移动端进程列表
- 进程名
- 进程 ID
- 重启按钮
- 关闭按钮

### FOC 密码查询结果
- 简单弹窗文本即可
