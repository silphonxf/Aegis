# Aegis v1.0.0 正式版发布说明

发布日期：2026-02-25

## ✅ 正式版范围

- 迭代1：MVP闭环（认证、巡检、自检、报表）
- 迭代2：管理与可视化（全局看板、资产管理、审计）
- 迭代3（第一阶段）：工具箱 + AI诊断mock + 审批流

## ✅ 前端UI完善

- 移动端与管理端统一为更清晰的卡片风格
- 顶部区域可视化版本标识（v1.0.0）
- 交互按钮增加视觉反馈，表格可读性增强

## ✅ 验证方式

```bash
cd /home/xf/.openclaw/workspace/code/aegis
./scripts/iteration3_smoke.sh
```

通过标准：脚本输出 `OK: iteration3 smoke passed`

## 已知限制（正式版说明）

1. 重启任务当前为审批mock，不执行真实重启。
2. AI诊断当前为mock逻辑，不依赖外部模型。
3. 多主机采集（SSH/Agent）将在后续版本提供。
