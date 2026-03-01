# 运维助手（Aegis）

运维助手是一个面向移动端的一体化运维应用，覆盖机房巡检、系统自查、报表分析、后台管理与全局监控。

## 核心目标
- 巡检数字化：扫码 / NFC 快速登记
- 自查标准化：日检 / 周检 / 年检可配置模板
- 数据可视化：巡检与自检报表、趋势分析
- 管理闭环：移动端执行 + 管理后台监管 + 超级管理员总览
- 平台兼容：Python 技术栈 + 达梦数据库 + 信创环境适配 + Docker 部署

## 仓库结构
- `docs/`：产品文档、开发计划、发布说明
- `backend/`：Python 后端（API、业务逻辑、数据层）
- `frontend-mobile/`：移动端前端（H5/PWA）
- `frontend-admin/`：后台管理前端
- `deploy/`：容器化与部署配置
- `scripts/`：开发与运维脚本

## 当前状态（v1.0.0 正式版）
- [x] 迭代1：MVP核心闭环
- [x] 迭代2：管理与可视化
- [x] 迭代3（第一阶段）：工具箱 + AI诊断mock + 审批流
- [x] 前后端联调与冒烟脚本

## 管理后台（5174）使用说明（v2）

### 访问地址
- 管理后台：`http://127.0.0.1:5174`
- 移动端：`http://127.0.0.1:5173`
- 后端 API：`http://127.0.0.1:8000`

### 界面结构
- 左侧主菜单：
  - 总览看板
  - 用户与系统
  - 资产管理
  - 高级工具
- 高级工具二级页签：
  - 运维审批
  - AI诊断
  - 模板与快照
  - 规则与审计
  - 调试与错误码

### 看板能力
- 登录后进入主界面
- 自动/手动刷新切换
- 异常系统筛选（状态 + 关键词）
- CPU/MEM/DISK 趋势火花图

详细变更与验收见：
- `docs/admin-ui-optimization-summary-2026-03-01.md`

## 快速验证

```bash
cd /home/xf/.openclaw/workspace/code/aegis
./scripts/iteration3_smoke.sh
```

更多见：
- `docs/release-v1.0.0.md`
- `docs/release-note-v0.3.md`
- `docs/iteration3-acceptance.md`
- `docs/dameng-setup.md`
