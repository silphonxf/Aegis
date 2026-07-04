# Handoff

## Status

已建立系统自检模块 thread，尚未改动业务代码。

已补充数据库自检方向，并在管理端增加数据库自检配置页。第一版复用系统接口保存数据库目标，使用 `selfcheck_skill` 生成 MySQL 自检配置。

## Recommended First Implementation Pass

1. 查看 `code/frontend-admin/index.html` 和 `code/frontend-admin/app.js` 的导航与页面组织方式。
2. 找出现有系统管理、自检记录或报表入口。
3. 新增“系统自检配置与记录”页面或 Tab，先展示系统和最近自检记录。
4. 复用已有 `/api/v1/selfchecks/*` 接口完成读取与 AI 自检动作。
5. 数据库自检配置先复用 `/api/v1/admin/systems`；后续再决定是否需要独立数据库配置表、加密密码字段或连接测试接口。
6. 再决定是否需要后端补字段、补筛选参数或补聚合接口。

## Verification

后续实现代码后，至少验证：

- 管理端 HTTPS 页面可打开。
- 默认管理员可进入系统自检模块。
- 自检记录列表能正常加载。
- AI 自检动作能返回状态 payload，缺少 selfcheck skill 时提示清晰。
- 数据库自检配置页能新增、编辑、停用 MySQL 配置。
- 不影响移动端现有自检页面。
