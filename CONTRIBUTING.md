# Aegis 协作规则

## Git 工作流

从 2026-04-05 起，功能开发统一使用 **功能分支**，不再直接向 `main` 提交功能改动。

### 规则
- 每做一个功能，先新建一个分支
- 分支命名建议：
  - `feat/<feature-name>`
  - `fix/<bug-name>`
  - `chore/<task-name>`
  - `docs/<topic-name>`
- 开发、提交、推送都在该分支完成
- **不要直接 merge 到 `main`**
- 由仓库 owner 手动审核并 merge 到 `main`

### 默认协作方式
1. 领取功能
2. 创建功能分支
3. 在功能分支开发与提交
4. 推送远端分支
5. 汇报：分支名 / commit / 改动说明 / 验证结果
6. 等待 owner 合并

### 示例
```bash
git checkout -b feat/toolbox-task-workflow
# 开发...
git add .
git commit -m "feat: improve toolbox task workflow"
git push origin feat/toolbox-task-workflow
```
