# Network Security Admin Module

## Goal

在管理端新增“网络安全”模块，集中承接移动端网络排障与安全研判能力：Ping 工具、抓包分析、IP 恶意研判。后续在这个 thread 中继续逐项调整每个功能。

## Current State

- 管理端侧边栏新增“网络安全”分组。
- Ping 工具新增管理端页面，复用 `/api/v1/toolbox/ping`。
- 抓包分析新增管理端页面，复用 `/api/v1/toolbox/capture/fetch` 与 `/api/v1/toolbox/capture/analyze`。
- 原“高危IP研判”入口从“运维审批与审计”移入“网络安全”，页面标题调整为“IP 恶意研判”，原 ThreatBook 能力保持不变。

## Key Files

- `code/frontend-admin/index.html`
- `code/frontend-admin/app.js`
- `code/frontend-admin/js/toolbox.js`
- `code/frontend-admin/js/threatbook.js`
- `code/backend/app/api/toolbox.py`
- `code/backend/app/api/admin.py`

## Decisions

- 本次不改后端接口，仅在管理端复用已有移动端工具接口，降低联调风险。
- IP 研判保留原 ThreatBook 脚本和后端接口，只移动导航归属与展示标题。
- 新增页面采用现有 `card`、`summary-strip`、`grid2`、`pre` 样式，保持管理端视觉一致。

## Next Steps

- 按实际使用反馈调整 Ping 输出摘要和异常状态样式。
- 抓包工具可继续补“请求头/方法/Body”等高级输入。
- IP 恶意研判后续可拆出本地规则、ThreatBook、封禁审批三个子视图。

## Handoff

打开管理端后，从左侧“网络安全”进入三个子功能。若需要继续调整某个功能，请在本 thread 中说明具体目标。
