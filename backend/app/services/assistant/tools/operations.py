from __future__ import annotations

import socket
import time
from typing import Any, Dict, Optional

import app.db.session as db_session_module
from app.models.tool_task import ToolTask
from app.models.system import System
from app.services.assistant.schemas import ToolSpec
from app.api.monitoring import _build_overview, _cpu_percent, _mem_percent, _disk_percent
from app.api.toolbox import _read_selected_logs, _resolve_time_range


def get_monitoring_overview(**_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        summary, items, abnormal = _build_overview(db)
        text = f"当前共 {summary.get('total', 0)} 个系统，绿色 {summary.get('green', 0)} 个，黄色 {summary.get('yellow', 0)} 个，红色 {summary.get('red', 0)} 个。"
        actions = []
        if abnormal:
            actions.append({"type": "open_abnormal_systems", "label": "查看异常系统", "payload": {"count": len(abnormal)}})
        return {
            "success": True,
            "summary": text,
            "data": {"summary": summary, "items": items, "abnormal_items": abnormal[:20]},
            "cards": [{"type": "system_status_overview", "title": "监控总览", "summary": text, "items": items[:10]}],
            "actions": actions,
        }
    finally:
        db.close()



def collect_local_status_snapshot(**_: Any) -> Dict[str, Any]:
    cpu = _cpu_percent()
    mem = _mem_percent()
    disk = _disk_percent('/')
    payload = {
        "cpu_usage": cpu,
        "mem_usage": mem,
        "disk_usage": disk,
        "host_online": "normal",
        "port_ok": "normal",
    }
    summary = f"本机状态已采集：CPU {cpu}% / 内存 {mem}% / 磁盘 {disk}%。"
    return {
        "success": True,
        "summary": summary,
        "data": payload,
        "cards": [{
            "type": "system_detail",
            "title": "本机状态采集",
            "detail": {
                "system_name": "本机",
                "system_code": "HOST-LOCAL",
                "env": "local",
                "status_snapshot": {
                    "status_color": "green",
                    "cpu_usage": cpu,
                    "mem_usage": mem,
                    "disk_usage": disk,
                    "captured_at": None,
                },
            },
        }],
        "actions": [],
    }



def run_ping_check(host: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    target = (host or '127.0.0.1').strip() or '127.0.0.1'
    started = time.time()
    ok = False
    error = None
    try:
        with socket.create_connection((target, 80), timeout=1):
            ok = True
    except OSError as e:
        error = str(e)
    elapsed_ms = int((time.time() - started) * 1000)
    summary = f"Ping/连通性检测：{target} {'可达' if ok else '可能异常'}，耗时 {elapsed_ms}ms。"
    return {
        "success": True,
        "summary": summary,
        "data": {"host": target, "ok": ok, "latency_ms": elapsed_ms, "error": error},
        "cards": [{"type": "tool_task", "title": "Ping 检测", "detail": {"host": target, "ok": ok, "latency_ms": elapsed_ms, "error": error}}],
        "actions": [],
    }



def run_port_check(host: Optional[str] = None, port: Optional[int] = None, **_: Any) -> Dict[str, Any]:
    target = (host or '127.0.0.1').strip() or '127.0.0.1'
    target_port = int(port or 8000)
    started = time.time()
    ok = False
    error = None
    try:
        with socket.create_connection((target, target_port), timeout=1):
            ok = True
    except OSError as e:
        error = str(e)
    elapsed_ms = int((time.time() - started) * 1000)
    summary = f"端口检测：{target}:{target_port} {'正常' if ok else '不通'}，耗时 {elapsed_ms}ms。"
    return {
        "success": True,
        "summary": summary,
        "data": {"host": target, "port": target_port, "ok": ok, "latency_ms": elapsed_ms, "error": error},
        "cards": [{"type": "tool_task", "title": "端口检测", "detail": {"host": target, "port": target_port, "ok": ok, "latency_ms": elapsed_ms, "error": error}}],
        "actions": [],
    }



def read_recent_error_logs(source: str = 'aegis', level: str = 'warning', quick_range: str = '1h', **_: Any) -> Dict[str, Any]:
    start_dt, end_dt, range_mode = _resolve_time_range(quick_range, None, None)
    content, source_detail = _read_selected_logs(source=source, file_name=None, level=level, start_dt=start_dt, end_dt=end_dt, lines=200)
    excerpt = '\n'.join([ln for ln in content.splitlines() if ln.strip()][:40]) if content else '未读取到相关日志。'
    summary = '已读取最近错误日志。' if content else '最近没有读取到符合条件的错误日志。'
    return {
        "success": True,
        "summary": summary,
        "data": {"source": source, "level": level, "range_mode": range_mode, "source_detail": source_detail, "content": content, "excerpt": excerpt},
        "cards": [{"type": "log_analysis", "title": "最近错误日志", "summary": summary, "items": [{"label": "来源", "value": source}, {"label": "级别", "value": level}, {"label": "范围", "value": quick_range}]}],
        "actions": [{"type": "quick_prompt", "label": "分析这段日志", "payload": {"message": excerpt[:1200] or '帮我分析最近错误日志'}}],
    }



def list_tool_tasks(status: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        q = db.query(ToolTask)
        if status:
            q = q.filter(ToolTask.status == status)
        items = q.order_by(ToolTask.created_at.desc()).limit(10).all()
        rows = []
        for item in items:
            rows.append({
                "id": item.id,
                "action": item.action,
                "target": item.target,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
        summary = f"最近工具任务 {len(rows)} 条。"
        return {
            "success": True,
            "summary": summary,
            "data": {"items": rows},
            "cards": [{"type": "inspection_records", "title": "工具任务", "summary": summary, "items": [{"label": f"{row['action']} / {row['target']}", "value": row['status']} for row in rows]}],
            "actions": [],
        }
    finally:
        db.close()



def register_operation_tools(registry) -> None:
    registry.register(ToolSpec(name='get_monitoring_overview', description='查询监控总览', handler=get_monitoring_overview))
    registry.register(ToolSpec(name='collect_local_status_snapshot', description='采集本机状态', handler=collect_local_status_snapshot))
    registry.register(ToolSpec(name='run_ping_check', description='执行 Ping/连通性检测', handler=run_ping_check))
    registry.register(ToolSpec(name='run_port_check', description='执行端口检测', handler=run_port_check))
    registry.register(ToolSpec(name='read_recent_error_logs', description='读取最近错误日志', handler=read_recent_error_logs))
    registry.register(ToolSpec(name='list_tool_tasks', description='查看最近工具任务', handler=list_tool_tasks))
