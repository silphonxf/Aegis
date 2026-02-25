import json
import socket
import subprocess
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.tool_task import ToolTask
from app.models.user import User
from app.schemas.toolbox import PingRequest, PortCheckRequest, RestartTaskRequest
from app.services.audit import log_action

router = APIRouter(prefix="/toolbox", tags=["toolbox"])


@router.post("/ping")
def ping_host(
    payload: PingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    cmd = ["ping", "-c", str(payload.count), "-W", "1", payload.host]
    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed_ms = int((time.time() - started) * 1000)

    ok = proc.returncode == 0
    result = {
        "host": payload.host,
        "ok": ok,
        "latency_ms": elapsed_ms,
        "output": (proc.stdout or proc.stderr)[-500:],
    }
    log_action(db, "toolbox_ping", "toolbox", current_user, {"host": payload.host, "ok": ok})
    return result


@router.post("/port-check")
def port_check(
    payload: PortCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    started = time.time()
    ok = False
    err = None
    try:
        with socket.create_connection((payload.host, payload.port), timeout=payload.timeout_ms / 1000):
            ok = True
    except OSError as e:
        err = str(e)

    elapsed_ms = int((time.time() - started) * 1000)
    log_action(db, "toolbox_port_check", "toolbox", current_user, {"host": payload.host, "port": payload.port, "ok": ok})
    return {
        "host": payload.host,
        "port": payload.port,
        "ok": ok,
        "latency_ms": elapsed_ms,
        "error": err,
    }


@router.post("/restart-task")
def create_restart_task(
    payload: RestartTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    task = ToolTask(
        action="restart",
        target=payload.target,
        status="pending_approval",
        result=json.dumps({"reason": payload.reason, "mock": True}, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log_action(db, "toolbox_create_restart_task", "tool_task", current_user, {"task_id": task.id, "target": task.target})
    return {"id": task.id, "status": task.status, "mock": True, "message": "仅创建审批任务，未执行重启"}


@router.get("/tasks")
def list_tasks(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(ToolTask)
    total = q.count()
    items = q.order_by(ToolTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id": t.id,
                "action": t.action,
                "target": t.target,
                "status": t.status,
                "result": t.result,
                "created_at": t.created_at,
            }
            for t in items
        ],
    }
