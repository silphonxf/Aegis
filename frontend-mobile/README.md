# frontend-mobile（移动端可测试界面）

当前是一个零构建依赖的 H5 联调页面，适合快速验证 Aegis 后端接口。

## 启动方式

```bash
cd frontend-mobile
python3 -m http.server 5173
```

打开：
- `http://127.0.0.1:5173`

## 后端准备

后端默认地址：`http://127.0.0.1:8000`

```bash
cd ../backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

默认账号（来自 seed）：
- 用户名：`admin`
- 密码：`admin123`

## 已支持页面能力

- 登录 + 持久化 token
- 获取当前用户信息
- 二维码解析巡检点
- 提交巡检记录 + 查看巡检历史
- 提交自检记录 + 查看自检历史
- 监控总览与规则查询
- 移动端工具箱（Ping、端口检测、重启任务审批mock）
- AI 诊断接口（mock）
- 错误码说明面板（AUTH_INVALID / VALIDATION_ERROR 等）
- 请求历史（自动记录 method/url/status/耗时/请求体/响应体）
- 一键导出联调日志 JSON（用于排障与复盘）

> 注意：`selfcheck` 提交需要已有 `template_id`，可先通过管理端创建模板。
