from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple
import json
import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.system import SystemLogConfig
from app.models.tool_task import ToolTask
from app.models.user import User
from app.schemas.capture import CaptureAnalyzeRequest, CaptureFetchRequest
from app.schemas.toolbox import ErrorLogSourceRequest, PingRequest, PortCheckRequest, RestartTaskRequest, TaskStatusUpdateRequest
from app.schemas.offline_ai import OfflineAnalyzeRequest
from app.services.ai_provider import run_offline_analyze
from app.services.audit import log_action

router = APIRouter(prefix="/toolbox", tags=["toolbox"])
logger = get_logger("toolbox")


def _extract_capture_excerpt(content: str, limit: int = 120) -> str:
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    return "\n".join(lines[:limit])


def _normalize_capture_url(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail={"code": "CAPTURE_URL_REQUIRED", "message": "请先输入要抓取的 URL"})
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail={"code": "CAPTURE_URL_INVALID", "message": "URL 格式不正确"})
    return value


def _fetch_url_capture(url: str) -> Dict[str, Any]:
    started = time.time()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AegisCaptureBot/1.0",
            "Accept": "text/html,application/json,text/plain,*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            status_code = getattr(resp, "status", 200)
            body_bytes = resp.read(12000)
            headers = dict(resp.headers.items())
            elapsed_ms = int((time.time() - started) * 1000)
            body_text = body_bytes.decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
            capture_lines = [
                f"URL: {url}",
                f"HTTP_STATUS: {status_code}",
                f"ELAPSED_MS: {elapsed_ms}",
                "RESPONSE_HEADERS:",
            ]
            for key, value in list(headers.items())[:20]:
                capture_lines.append(f"{key}: {value}")
            capture_lines.extend([
                "",
                "RESPONSE_BODY_EXCERPT:",
                body_text[:8000],
            ])
            return {
                "url": url,
                "status_code": status_code,
                "elapsed_ms": elapsed_ms,
                "content_type": headers.get("Content-Type", ""),
                "content": "\n".join(capture_lines).strip(),
            }
    except urllib.error.HTTPError as e:
        body_text = e.read(8000).decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise HTTPException(status_code=400, detail={
            "code": "CAPTURE_FETCH_FAILED",
            "message": f"抓取失败：HTTP {e.code}",
            "extra": body_text[:500],
        })
    except urllib.error.URLError as e:
        raise HTTPException(status_code=400, detail={"code": "CAPTURE_FETCH_FAILED", "message": f"抓取失败：{e.reason}"})
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "CAPTURE_FETCH_FAILED", "message": f"抓取失败：{e}"})


def _parse_datetime_input(value: Optional[str]) -> Optional[datetime]:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail={"code": "INVALID_DATETIME", "message": f"时间格式不正确：{text}"})


def _resolve_time_range(quick_range: Optional[str], start_at: Optional[str], end_at: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime], str]:
    start_dt = _parse_datetime_input(start_at)
    end_dt = _parse_datetime_input(end_at)
    if start_dt or end_dt:
        if not (start_dt and end_dt):
            raise HTTPException(status_code=400, detail={"code": "TIME_RANGE_INCOMPLETE", "message": "开始时间和结束时间需要同时选择"})
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail={"code": "TIME_RANGE_INVALID", "message": "开始时间不能晚于结束时间"})
        return start_dt, end_dt, "calendar"

    mapping = {"1h": 1, "3h": 3, "6h": 6}
    hours = mapping.get((quick_range or "1h").strip(), 1)
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(hours=hours)
    return start_dt, end_dt, quick_range or "1h"


def _level_keyword_pattern(level: str) -> str:
    level = (level or "warning").lower()
    if level == "info":
        return r"INFO|WARNING|ERROR|CRITICAL|Exception|Traceback|\[req:"
    if level == "error":
        return r"ERROR|CRITICAL|Exception|Traceback"
    return r"WARNING|ERROR|CRITICAL|Exception|Traceback"


def _matches_time_range(line: str, start_dt: Optional[datetime], end_dt: Optional[datetime]) -> bool:
    if not (start_dt and end_dt):
        return True
    if len(line) < 16:
        return True

    parsed = None
    for candidate in (line[:19], line[:16]):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(candidate, fmt)
                break
            except ValueError:
                continue
        if parsed:
            break

    if not parsed:
        return True
    return start_dt <= parsed <= end_dt


def _collect_log_files(source: str) -> list[str]:
    if source == "system":
        candidates = ["/var/log/syslog", "/var/log/messages"]
        return [path for path in candidates if os.path.exists(path)]

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    logs_dir = os.path.join(repo_root, ".logs")
    candidates = [
        os.path.join(logs_dir, name)
        for name in [
            "backend.log",
            "backend-https.log",
            "frontend-mobile.log",
            "frontend-mobile-https.log",
            "frontend-admin.log",
            "frontend-admin-https.log",
        ]
        if os.path.exists(os.path.join(logs_dir, name))
    ]

    tmp_candidates = [
        "/tmp/aegis-backend-https.log",
        "/tmp/aegis-frontend-mobile-5173-https.log",
        "/tmp/aegis-frontend-admin-5174-https.log",
        "/tmp/aegis-frontend-mobile.log",
        "/tmp/aegis-frontend-admin.log",
        "/tmp/aegis-frontend-mobile-https.log",
        "/tmp/aegis-frontend-admin-https.log",
    ]
    candidates.extend([path for path in tmp_candidates if os.path.exists(path)])

    seen = set()
    ordered = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def _log_file_aliases(file_name: str) -> list[str]:
    alias_map = {
        "backend-https.log": ["backend.log"],
        "frontend-mobile-https.log": ["frontend-mobile.log"],
        "frontend-admin-https.log": ["frontend-admin.log"],
        "aegis-backend-https.log": ["backend-https.log", "backend.log"],
        "aegis-frontend-mobile-5173-https.log": ["frontend-mobile-https.log", "frontend-mobile.log"],
        "aegis-frontend-admin-5174-https.log": ["frontend-admin-https.log", "frontend-admin.log"],
    }
    return [file_name, *alias_map.get(file_name, [])]


def _read_log_tail(path: str, max_lines: int = 20000) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return list(deque(fh, maxlen=max_lines))


def _read_selected_logs(source: str, file_name: Optional[str], level: str, start_dt: Optional[datetime], end_dt: Optional[datetime], lines: int, configured_paths: Optional[list[str]] = None) -> Tuple[str, str]:
    candidates = configured_paths if configured_paths is not None else _collect_log_files(source)
    if not candidates:
        return "", "未找到可用日志文件"

    if file_name:
        if os.path.isabs(file_name):
            selected = [path for path in candidates if os.path.abspath(path) == os.path.abspath(file_name)]
        else:
            accepted_names = set(_log_file_aliases(file_name))
            selected = [path for path in candidates if os.path.basename(path) in accepted_names]
        if not selected:
            raise HTTPException(status_code=400, detail={"code": "LOG_FILE_NOT_FOUND", "message": f"未找到日志文件：{file_name}"})
        candidates = selected

    pattern = re.compile(_level_keyword_pattern(level), re.IGNORECASE)
    chunks = []
    used_sources = []
    for path in candidates:
        try:
            lines_buf = _read_log_tail(path)
        except OSError:
            continue

        matched = []
        for raw in lines_buf:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if not _matches_time_range(line, start_dt, end_dt):
                continue
            if pattern.search(line):
                matched.append(line)
        if matched:
            chunks.append(f"===== {os.path.basename(path)} =====\n" + "\n".join(matched[-lines:]))
            used_sources.append(path)

    if chunks:
        return "\n\n".join(chunks)[-120000:], ", ".join(used_sources)

    if (level or "warning").lower() == "info":
        for path in candidates:
            try:
                lines_buf = _read_log_tail(path)
            except OSError:
                continue
            matched = []
            for raw in lines_buf:
                line = raw.rstrip("\n")
                if not line.strip():
                    continue
                if not _matches_time_range(line, start_dt, end_dt):
                    continue
                matched.append(line)
            if matched:
                chunks.append(f"===== {os.path.basename(path)} =====\n" + "\n".join(matched[-lines:]))
                used_sources.append(path)

        if chunks:
            return "\n\n".join(chunks)[-120000:], ", ".join(used_sources)

    return "", "未命中符合筛选条件的日志"


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
    logger.info("Ping检测请求: user=%s host=%s count=%s", current_user.username, payload.host, payload.count)
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
    logger.info("Ping检测完成: host=%s ok=%s latency_ms=%s", payload.host, ok, elapsed_ms)
    log_action(db, "toolbox_ping", "toolbox", current_user, {"host": payload.host, "ok": ok})
    return result


@router.post("/port-check")
def port_check(
    payload: PortCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    logger.info("端口检测请求: user=%s host=%s port=%s timeout_ms=%s", current_user.username, payload.host, payload.port, payload.timeout_ms)
    started = time.time()
    ok = False
    err = None
    try:
        with socket.create_connection((payload.host, payload.port), timeout=payload.timeout_ms / 1000):
            ok = True
    except OSError as e:
        err = str(e)

    elapsed_ms = int((time.time() - started) * 1000)
    logger.info("端口检测完成: host=%s port=%s ok=%s latency_ms=%s", payload.host, payload.port, ok, elapsed_ms)
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
    source: str = "aegis",
    file_name: Optional[str] = None,
    quick_range: Optional[str] = "1h",
    start_at: Optional[str] = None,
    end_at: Optional[str] = None,
    level: str = "warning",
    lines: int = 5000,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    payload = ErrorLogSourceRequest(
        source=source,
        file_name=file_name,
        quick_range=quick_range,
        start_at=start_at,
        end_at=end_at,
        level=level,
        lines=lines,
    )
    if payload.file_name and not payload.start_at and not payload.end_at:
        start_dt, end_dt, range_mode = None, None, "selected_file"
    else:
        start_dt, end_dt, range_mode = _resolve_time_range(payload.quick_range, payload.start_at, payload.end_at)
    logger.info(
        "读取错误日志请求: user=%s source=%s file_name=%s level=%s range_mode=%s lines=%s",
        current_user.username,
        payload.source,
        payload.file_name,
        payload.level,
        range_mode,
        payload.lines,
    )

    configured_paths = None
    if payload.source == "system":
        q = db.query(SystemLogConfig.absolute_path).filter(SystemLogConfig.is_active.is_(True))
        if payload.file_name and os.path.isabs(payload.file_name):
            q = q.filter(SystemLogConfig.absolute_path == payload.file_name)
        configured_paths = [row.absolute_path for row in q.all()]
        if payload.file_name and os.path.isabs(payload.file_name) and not configured_paths:
            raise HTTPException(status_code=400, detail={"code": "LOG_FILE_NOT_CONFIGURED", "message": "该日志路径未在管理端系统日志配置中启用"})

    content, source_detail = _read_selected_logs(
        source=payload.source,
        file_name=payload.file_name,
        level=payload.level,
        start_dt=start_dt,
        end_dt=end_dt,
        lines=payload.lines,
        configured_paths=configured_paths,
    )
    if payload.source == "system":
        empty_message = "未读取到系统日志，请确认系统日志文件存在且筛选条件合理。"
    else:
        empty_message = "未读取到 Aegis 应用日志，请确认日志文件已生成，或放宽时间范围/日志级别筛选。"

    if not content:
        logger.warning("读取错误日志结果为空: source=%s detail=%s", payload.source, source_detail)
        content = empty_message

    log_action(
        db,
        "toolbox_read_error_logs",
        "toolbox",
        current_user,
        {
            "source": payload.source,
            "file_name": payload.file_name,
            "quick_range": payload.quick_range,
            "start_at": payload.start_at,
            "end_at": payload.end_at,
            "level": payload.level,
            "lines": payload.lines,
            "source_detail": source_detail[:200],
        },
    )

    excerpt_lines = [ln for ln in content.splitlines() if ln.strip()]
    keywords = [kw for kw in ["info", "warning", "error", "exception", "fatal", "traceback", "timeout"] if kw in content.lower()]
    logger.info("读取错误日志完成: source=%s detail=%s line_count=%s matched_keywords=%s", payload.source, source_detail, len(excerpt_lines), ",".join(keywords) or "-")
    return {
        "source": payload.source,
        "file_name": payload.file_name,
        "quick_range": payload.quick_range,
        "start_at": payload.start_at,
        "end_at": payload.end_at,
        "level": payload.level,
        "range_mode": range_mode,
        "source_detail": source_detail,
        "content": content,
        "excerpt": "\n".join(excerpt_lines[:50]),
        "line_count": len(excerpt_lines),
        "truncated": len(content) >= 120000,
        "matched_keywords": keywords,
        "available_files": [os.path.basename(path) for path in _collect_log_files(payload.source)],
    }


@router.post("/restart-task")
def create_restart_task(
    payload: RestartTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    logger.info("创建重启审批任务: user=%s target=%s", current_user.username, payload.target)
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
    logger.info("创建重启审批任务成功: task_id=%s status=%s", task.id, task.status)
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
    logger.info("查询工具任务: status=%s page=%s size=%s", status, page, size)
    page = max(page, 1)
    size = min(max(size, 1), 100)
    q = db.query(ToolTask)
    if status:
        q = q.filter(ToolTask.status == status)
    total = q.count()
    items = q.order_by(ToolTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    logger.info("查询工具任务完成: total=%s returned=%s", total, len(items))
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
    logger.info("更新工具任务状态: user=%s task_id=%s target_status=%s", current_user.username, task_id, payload.status)
    task = db.query(ToolTask).filter(ToolTask.id == task_id).first()
    if not task:
        logger.warning("更新工具任务状态失败: task_id=%s 不存在", task_id)
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
        logger.warning("更新工具任务状态失败: task_id=%s from=%s to=%s 不合法", task_id, current, target)
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

    logger.info("更新工具任务状态完成: task_id=%s from=%s to=%s executor=%s", task.id, current, target, executor)
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


@router.post("/capture/fetch")
def fetch_capture_from_url(
    payload: CaptureFetchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    url = _normalize_capture_url(payload.url)
    logger.info("抓取URL请求: user=%s url=%s", current_user.username, url)
    result = _fetch_url_capture(url)
    logger.info("抓取URL完成: url=%s status_code=%s elapsed_ms=%s", url, result.get("status_code"), result.get("elapsed_ms"))
    log_action(
        db,
        "toolbox_capture_fetch",
        "toolbox",
        current_user,
        {"url": url, "status_code": result.get("status_code"), "elapsed_ms": result.get("elapsed_ms")},
    )
    return result


@router.post("/capture/analyze")
def analyze_capture_result(
    payload: CaptureAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    logger.info("抓包分析请求: user=%s source=%s severity=%s", current_user.username, payload.source, payload.severity)
    detail_parts = [f"来源：{payload.source}"]
    if payload.note:
        detail_parts.append(f"备注：{payload.note}")
    detail_parts.append("抓包结果摘录：\n" + _extract_capture_excerpt(payload.content))

    result = run_offline_analyze(
        OfflineAnalyzeRequest(
            title=payload.title,
            detail="\n\n".join(detail_parts),
            severity=payload.severity,
            source_type="capture_result",
            source_ref=payload.source,
        )
    )

    logger.info("抓包分析完成: source=%s mode=%s severity=%s elapsed_ms=%s", payload.source, result.get("mode"), result.get("severity", payload.severity), result.get("elapsed_ms"))
    log_action(
        db,
        "toolbox_capture_analyze",
        "toolbox",
        current_user,
        {"source": payload.source, "severity": payload.severity, "mode": result.get("mode")},
    )
    return {
        "title": payload.title,
        "mode": result.get("mode", "rule_fallback"),
        "severity": result.get("severity", payload.severity),
        "summary": result.get("summary", ""),
        "matched_rules": result.get("matched_rules", []),
        "suggestions": result.get("suggestions", []),
        "excerpt": result.get("excerpt", ""),
        "elapsed_ms": result.get("elapsed_ms", 0),
        "fallback_reason": result.get("fallback_reason"),
    }
