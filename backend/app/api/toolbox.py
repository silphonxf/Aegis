from typing import Any, Dict, List, Optional, Set, Tuple
import json
import os
import socket
import subprocess
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.tool_task import ToolTask
from app.models.user import User
from app.schemas.toolbox import PingRequest, PortCheckRequest, RestartTaskRequest, TaskStatusUpdateRequest
from app.services.audit import log_action

router = APIRouter(prefix="/toolbox", tags=["toolbox"])


def _read_error_logs(hours: int, lines: int) -> Tuple[str, str]:
    """读取系统 error 日志，优先 journalctl，其次 syslog/messages。"""
    commands = [
        [
            "journalctl",
            "--since",
            f"-{hours} hour",
            "-p",
            "err",
            "--no-pager",
            "-n",
            str(lines),
            "-o",
            "short-iso",
        ],
    ]

    syslog_path = "/var/log/syslog"
    messages_path = "/var/log/messages"
    if os.path.exists(syslog_path):
        commands.append(["bash", "-lc", f"tail -n 20000 {syslog_path} | grep -Ei 'error|exception|fatal|traceback' | tail -n {lines}"])
    if os.path.exists(messages_path):
        commands.append(["bash", "-lc", f"tail -n 20000 {messages_path} | grep -Ei 'error|exception|fatal|traceback' | tail -n {lines}"])

    last_err = ""
    for cmd in commands:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if proc.returncode == 0 and (proc.stdout or "").strip():
                return proc.stdout[-120000:], " ".join(cmd)
            last_err = (proc.stderr or proc.stdout or "").strip()
        except Exception as e:
            last_err = str(e)

    return "", last_err


def _load_task_result(task: ToolTask) -> dict:
    if not task.result:
        return {}
    try:
        return json.loads(task.result)
    except Exception:
        return {"raw": task.result}


def _write_task_result(task: ToolTask, *, note: Optional[str] = None, executor: Optional[str] = None, success: Optional[bool] = None, error: Optional[str] = None):
    data = _load_task_result(task)
    if note is not None:
        data["note"] = note
    if executor is not None:
        data["executor"] = executor
    if task.started_at is not None:
        data["started_at"] = task.started_at.isoformat()
    if task.finished_at is not None:
        data["finished_at"] = task.finished_at.isoformat()
    if success is not None:
        data["success"] = success
    if error is not None:
        data["error"] = error
    task.result = json.dumps(data, ensure_ascii=False)
    return data


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


@router.get("/error-logs")
def read_error_logs(
    hours: int = 24,
    lines: int = 5000,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    hours = min(max(hours, 1), 168)
    lines = min(max(lines, 100), 5000)

    content, source = _read_error_logs(hours=hours, lines=lines)
    if not content:
        content = "未读取到 error 日志，请确认系统日志权限（journalctl/syslog）。"

    log_action(
        db,
        "toolbox_read_error_logs",
        "toolbox",
        current_user,
        {"hours": hours, "lines": lines, "source": source[:200]},
    )

    excerpt_lines = [ln for ln in content.splitlines() if ln.strip()]
    keywords = [kw for kw in ["error", "exception", "fatal", "traceback", "timeout"] if kw in content.lower()]
    return {
        "hours": hours,
        "lines": lines,
        "source": source,
        "content": content,
        "excerpt": "\n".join(excerpt_lines[:50]),
        "line_count": len(excerpt_lines),
        "truncated": len(content) >= 120000,
        "matched_keywords": keywords,
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
        result=json.dumps(
            {
                "reason": payload.reason,
                "note": None,
                "executor": "mock",
                "started_at": None,
                "finished_at": None,
                "success": None,
                "error": None,
            },
            ensure_ascii=False,
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log_action(db, "toolbox_create_restart_task", "tool_task", current_user, {"task_id": task.id, "target": task.target})
    return {
        "id": task.id,
        "status": task.status,
        "result": _load_task_result(task),
        "mock": True,
        "message": "仅创建审批任务，未执行重启",
    }


@router.get("/tasks")
def list_tasks(
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(ToolTask)
    if status:
        q = q.filter(ToolTask.status == status)
    total = q.count()
    items = q.order_by(ToolTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "filters": {"status": status},
        "items": [
            {
                "id": t.id,
                "action": t.action,
                "target": t.target,
                "status": t.status,
                "executor": t.executor,
                "started_at": t.started_at,
                "finished_at": t.finished_at,
                "result": _load_task_result(t),
                "created_at": t.created_at,
            }
            for t in items
        ],
    }


@router.put("/tasks/{task_id}/status")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
):
    task = db.query(ToolTask).filter(ToolTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})

    current = task.status
    target = payload.status
    allowed = {
        "pending_approval": {"approved", "rejected", "cancelled"},
        "approved": {"running", "cancelled"},
        "running": {"done", "failed", "cancelled"},
        "rejected": set(),
        "done": set(),
        "failed": set(),
        "cancelled": set(),
    }
    if target not in allowed.get(current, set()):
        raise HTTPException(status_code=400, detail={"code": "TASK_STATUS_INVALID", "message": f"不允许从 {current} 变更到 {target}"})

    task.status = target
    executor = payload.executor or task.executor or current_user.username
    task.executor = executor

    if target == "running" and task.started_at is None:
        task.started_at = datetime.utcnow()
    if target in {"done", "failed", "rejected", "cancelled"} and task.finished_at is None:
        if task.started_at is None and target in {"done", "failed"}:
            task.started_at = datetime.utcnow()
        task.finished_at = datetime.utcnow()

    success = None
    error = None
    if target == "done":
        success = True
    elif target in {"failed", "rejected", "cancelled"}:
        success = False
        error = payload.note if target == "failed" else None

    result = _write_task_result(task, note=payload.note, executor=executor, success=success, error=error)
    db.commit()
    db.refresh(task)

    log_action(
        db,
        "toolbox_update_task_status",
        "tool_task",
        current_user,
        {"task_id": task.id, "from": current, "to": target, "executor": executor},
    )
    return {
        "id": task.id,
        "status": task.status,
        "executor": task.executor,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "result": result,
    }
