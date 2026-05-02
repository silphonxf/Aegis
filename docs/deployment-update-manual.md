# Aegis 日常更新手册

适用场景：当前服务器已按 `Python 3.9 + FastAPI + SQLite/Nginx + systemd` 方式部署完成，后续需要拉代码、更新前后端、执行迁移、重启服务时使用。

> 当前约束：Aegis 默认按 **Python 3.9** 兼容方案维护，不使用高于 Python 3.9 的版本做日常部署。

---

## 1. 目录与服务约定

- 项目目录：`/opt/Aegis`
- 后端目录：`/opt/Aegis/backend`
- 管理端静态目录：`/var/www/aegis/admin`
- 移动端静态目录：`/var/www/aegis/mobile`
- 后端 systemd 服务名：`aegis-api`
- Nginx 服务名：`nginx`

---

## 2. 更新前建议先看状态

### 查看后端服务状态
```bash
sudo systemctl status aegis-api --no-pager
```

### 查看后端日志
```bash
sudo journalctl -u aegis-api -n 100 --no-pager
```

### 查看 Nginx 状态
```bash
sudo systemctl status nginx --no-pager
```

---

## 3. 通用更新第一步：拉最新代码

```bash
cd /opt/Aegis
git pull
```

如果 `git pull` 失败，优先检查仓库远程是否已切到 SSH：

```bash
git remote -v
```

推荐使用：

```bash
git@github.com:silphonxf/Aegis.git
```

---

## 4. 仅后端 Python 代码改动

适用情况：
- `backend/app/*.py`
- `backend/alembic/env.py`
- 普通业务逻辑修改
- 没改 `requirements.txt`
- 没改数据库结构

执行：

```bash
cd /opt/Aegis
git pull
sudo systemctl restart aegis-api
sudo systemctl status aegis-api --no-pager
```

如果要追日志：

```bash
sudo journalctl -u aegis-api -f
```

---

## 5. 后端依赖变更（requirements.txt 改了）

适用情况：
- `backend/requirements.txt` 有新增、删除或版本调整

执行：

```bash
cd /opt/Aegis
git pull

cd /opt/Aegis/backend
source .venv/bin/activate
pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

sudo systemctl restart aegis-api
sudo systemctl status aegis-api --no-pager
```

---

## 6. 数据库结构改动（需要迁移）

适用情况：
- `backend/alembic/versions/*` 变化
- `backend/app/models/*` 改动涉及表结构
- 新增字段 / 新增表 / 修改索引

执行：

```bash
cd /opt/Aegis
git pull

cd /opt/Aegis/backend
source .venv/bin/activate
alembic upgrade head

sudo systemctl restart aegis-api
sudo systemctl status aegis-api --no-pager
```

### 迁移成功后的简单检查
```bash
curl http://127.0.0.1:8000/healthz
```

---

## 7. 什么时候需要重建 Python 虚拟环境

通常 **不要** 每次更新都重建 `.venv`。

只有以下情况才建议重建：

1. Python 版本变化
2. `.venv` 已损坏
3. 依赖冲突严重，普通 `pip install -r requirements.txt` 已无法修复
4. 需要做一次彻底干净的环境重装

### 重建 `.venv` 的标准步骤
```bash
cd /opt/Aegis/backend

deactivate 2>/dev/null || true
mv .venv .venv.bak_$(date +%Y%m%d%H%M%S)

/usr/local/python3.9/bin/python3.9 -m venv .venv
source .venv/bin/activate

pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

如果后端依赖数据库迁移，再执行：

```bash
alembic upgrade head
```

最后重启服务：

```bash
sudo systemctl restart aegis-api
```

---

## 8. 前端静态文件改动如何更新

当前前端不是 Node 打包型项目，默认按仓库中的静态文件直接部署。

适用情况：
- `frontend-admin/` 有改动
- `frontend-mobile/` 有改动

执行：

```bash
cd /opt/Aegis
git pull

sudo cp -r /opt/Aegis/frontend-admin/* /var/www/aegis/admin/
sudo cp -r /opt/Aegis/frontend-mobile/* /var/www/aegis/mobile/

sudo systemctl reload nginx
```

> 如果只是静态文件变化，很多时候 Nginx 不 reload 也能生效；但 `reload` 更稳。

---

## 9. 前后端一起更新的常用流程

```bash
cd /opt/Aegis
git pull

cd /opt/Aegis/backend
source .venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
alembic upgrade head

sudo systemctl restart aegis-api

sudo cp -r /opt/Aegis/frontend-admin/* /var/www/aegis/admin/
sudo cp -r /opt/Aegis/frontend-mobile/* /var/www/aegis/mobile/
sudo systemctl reload nginx
```

---

## 10. 常见问题判断

### 1）`ModuleNotFoundError: No module named xxx`
原因：缺 Python 依赖。
处理：

```bash
cd /opt/Aegis/backend
source .venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
sudo systemctl restart aegis-api
```

如果 `requirements.txt` 本身漏依赖，需要先补到仓库再重新拉代码。

### 2）`ValidationError` / `SECRET_KEY field required`
原因：`.env` 缺配置。
处理：检查：

```bash
/opt/Aegis/backend/.env
```

至少要保证这些字段存在：
- `SECRET_KEY`
- `INIT_ADMIN_PASSWORD`
- `DATABASE_URL`

### 3）`git pull` 走 HTTPS 超时
原因：服务器出站 443 不稳定。
处理：优先改成 SSH 远程：

```bash
git remote set-url origin git@github.com:silphonxf/Aegis.git
```

### 4）修改 `.env` 后要不要重建 Python 环境？
不用。
通常只需要：

```bash
cd /opt/Aegis/backend
source .venv/bin/activate
sudo systemctl restart aegis-api
```

如果涉及首次迁移或配置影响启动，也可以补跑：

```bash
alembic upgrade head
```

---

## 11. 验收命令

### 后端健康检查
```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1/healthz
```

### 查看管理端页面是否可访问
浏览器访问：
- `http://服务器IP/admin/`
- `http://服务器IP/mobile/`

### 查看 Nginx 配置是否正常
```bash
sudo nginx -t
```

---

## 12. 回滚建议

如果某次更新后服务异常：

1. 先看日志
```bash
sudo journalctl -u aegis-api -n 100 --no-pager
```

2. 如果是代码问题，回退 git 提交
```bash
cd /opt/Aegis
git log --oneline -n 10
```

3. 如果是依赖问题，优先重新安装 requirements
4. 如果是环境彻底乱了，再考虑回退 `.venv.bak_*`

---

## 13. 当前部署建议

- 默认优先用 SQLite 跑通
- 正式切信创库时再切达梦
- 后续开发与部署默认保持 **Python 3.9 兼容**
- 日常更新优先遵循：`git pull ->（必要时 pip install / alembic）-> restart service`
