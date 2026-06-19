# 运维助手 ER 模型（MVP v1）

## 核心实体

1. **users**（用户）
   - id, username, password_hash, role_id, is_active, created_at

2. **roles**（角色）
   - id, code (inspector/admin/super_admin), name

3. **systems**（被管系统）
   - id, system_code, name, owner_user_id, env, is_active

4. **inspection_points**（巡检点）
   - id, system_id, point_code, qr_content, location, is_active

5. **inspection_records**（巡检记录）
   - id, system_id, point_id, inspector_id, result, note, inspected_at

6. **checklist_templates**（自检模板）
   - id, system_id, check_type(daily/weekly/yearly), name, is_active

7. **selfcheck_records**（自检记录）
   - id, system_id, template_id, operator_id, result, summary, checked_at

8. **system_status_snapshots**（系统状态快照）
   - id, system_id, host_online, port_ok, cpu_level, mem_level, disk_level,
     last_inspection_result, last_selfcheck_result, status_color, captured_at

## 关系说明
- roles 1:N users
- users 1:N systems（owner）
- systems 1:N inspection_points
- systems 1:N inspection_records
- inspection_points 1:N inspection_records
- systems 1:N checklist_templates
- checklist_templates 1:N selfcheck_records
- systems 1:N selfcheck_records
- systems 1:N system_status_snapshots

## 数据库适配建议
- 主键使用 BIGINT
- 时间字段统一 TIMESTAMP
- 枚举采用 VARCHAR + CHECK 约束
- 关键索引：
  - inspection_records(system_id, inspected_at)
  - selfcheck_records(system_id, checked_at)
  - system_status_snapshots(system_id, captured_at)

