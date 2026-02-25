import csv
import os
import shutil
import socket
import time
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.rule import StatusRule
from app.models.system import System, SystemStatusSnapshot
from app.models.user import User
from app.schemas.rule import StatusRuleUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _build_overview(db: Session):
    systems = db.query(System).all()

    items = []
    for s in systems:
        snap = (
            db.query(SystemStatusSnapshot)
            .filter(SystemStatusSnapshot.system_id == s.id)
            .order_by(SystemStatusSnapshot.captured_at.desc())
            .first()
        )
        if snap:
            color = snap.status_color
            cpu_level = snap.cpu_level
            mem_level = snap.mem_level
            disk_level = snap.disk_level
            captured_at = snap.captured_at
        else:
            color = "green"
            cpu_level = mem_level = disk_level = "unknown"
            captured_at = None

        items.append(
            {
                "system_id": s.id,
                "system_code": s.system_code,
                "system_name": s.name,
                "env": s.env,
                "status_color": color,
                "cpu_level": cpu_level,
                "mem_level": mem_level,
                "disk_level": disk_level,
                "captured_at": captured_at,
            }
        )

    summary = {
        "green": sum(1 for i in items if i["status_color"] == "green"),
        "yellow": sum(1 for i in items if i["status_color"] == "yellow"),
        "red": sum(1 for i in items if i["status_color"] == "red"),
        "total": len(items),
    }

    abnormal = [i for i in items if i["status_color"] in {"yellow", "red"}]
    return summary, items, abnormal


def _normalize_metric(value: int | None, warn: int, critical: int) -> str:
    if value is None:
        return "unknown"
    if value >= critical:
        return "critical"
    if value >= warn:
        return "warning"
    return "normal"


def _calc_color(levels: list[str], host_online: str, port_ok: str, last_inspection_result: str, last_selfcheck_result: str) -> str:
    if host_online == "abnormal" or port_ok == "abnormal":
        return "red"
    if last_inspection_result == "abnormal" or last_selfcheck_result == "critical":
        return "red"
    if "critical" in levels:
        return "red"
    if last_selfcheck_result == "warning" or "warning" in levels:
        return "yellow"
    return "green"


def _cpu_percent() -> int:
    def read_cpu_times() -> tuple[int, int]:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            first = f.readline().split()
        values = [int(x) for x in first[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        return idle, total

    idle1, total1 = read_cpu_times()
    time.sleep(0.2)
    idle2, total2 = read_cpu_times()
    total_diff = max(total2 - total1, 1)
    idle_diff = max(idle2 - idle1, 0)
    usage = int(round((1 - idle_diff / total_diff) * 100))
    return max(0, min(100, usage))


def _mem_percent() -> int:
    info = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f:
            k, v = line.split(":", 1)
            info[k] = int(v.strip().split()[0])
    total = max(info.get("MemTotal", 1), 1)
    available = info.get("MemAvailable", 0)
    usage = int(round((1 - available / total) * 100))
    return max(0, min(100, usage))


def _disk_percent(path: str = "/") -> int:
    usage = shutil.disk_usage(path)
    pct = int(round((usage.used / max(usage.total, 1)) * 100))
    return max(0, min(100, pct))


def _tcp_check(host: str = "127.0.0.1", port: int = 8000, timeout: float = 1.0) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "normal"
    except OSError:
        return "abnormal"


@router.get("/rules")
def get_rules(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rule = db.query(StatusRule).order_by(StatusRule.id.asc()).first()
    if not rule:
        rule = StatusRule()
        db.add(rule)
        db.commit()
        db.refresh(rule)
    return {
        "cpu_warn": rule.cpu_warn,
        "cpu_critical": rule.cpu_critical,
        "mem_warn": rule.mem_warn,
        "mem_critical": rule.mem_critical,
        "disk_warn": rule.disk_warn,
        "disk_critical": rule.disk_critical,
    }


@router.put("/rules")
def update_rules(
    payload: StatusRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
):
    rule = db.query(StatusRule).order_by(StatusRule.id.asc()).first()
    if not rule:
        rule = StatusRule()
        db.add(rule)
        db.flush()

    for k, v in payload.model_dump().items():
        setattr(rule, k, v)

    db.commit()
    db.refresh(rule)
    log_action(db, "update_status_rules", "status_rules", current_user, payload.model_dump())
    return {"updated": True}


@router.get("/overview")
def monitoring_overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    summary, items, abnormal = _build_overview(db)
    return {"summary": summary, "items": items, "abnormal_items": abnormal[:20]}


@router.post("/collect/local")
def collect_local_snapshot(
    system_code: str = "HOST-LOCAL-001",
    env: str = "prod",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    hostname = socket.gethostname()
    system = db.query(System).filter(System.system_code == system_code).first()
    if not system:
        system = System(system_code=system_code, name=f"本机-{hostname}", env=env)
        db.add(system)
        db.commit()
        db.refresh(system)

    rule = db.query(StatusRule).order_by(StatusRule.id.asc()).first()
    if not rule:
        rule = StatusRule()
        db.add(rule)
        db.commit()
        db.refresh(rule)

    cpu_usage = _cpu_percent()
    mem_usage = _mem_percent()
    disk_usage = _disk_percent("/")
    host_online = "normal"
    port_ok = _tcp_check("127.0.0.1", 8000)

    cpu_level = _normalize_metric(cpu_usage, rule.cpu_warn, rule.cpu_critical)
    mem_level = _normalize_metric(mem_usage, rule.mem_warn, rule.mem_critical)
    disk_level = _normalize_metric(disk_usage, rule.disk_warn, rule.disk_critical)

    status_color = _calc_color(
        [cpu_level, mem_level, disk_level],
        host_online=host_online,
        port_ok=port_ok,
        last_inspection_result="unknown",
        last_selfcheck_result="unknown",
    )

    snap = SystemStatusSnapshot(
        system_id=system.id,
        host_online=host_online,
        port_ok=port_ok,
        cpu_level=cpu_level,
        mem_level=mem_level,
        disk_level=disk_level,
        last_inspection_result="unknown",
        last_selfcheck_result="unknown",
        status_color=status_color,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    payload = {
        "system_id": system.id,
        "system_code": system.system_code,
        "hostname": hostname,
        "cpu_usage": cpu_usage,
        "mem_usage": mem_usage,
        "disk_usage": disk_usage,
        "cpu_level": cpu_level,
        "mem_level": mem_level,
        "disk_level": disk_level,
        "status_color": status_color,
    }
    log_action(db, "collect_local_snapshot", "monitoring", current_user, payload)
    return payload


@router.get("/abnormal/export")
def export_abnormal_csv(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _, _, abnormal = _build_overview(db)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["system_id", "system_code", "system_name", "env", "status_color", "cpu_level", "mem_level", "disk_level", "captured_at"])
    for i in abnormal:
        writer.writerow([
            i["system_id"],
            i["system_code"],
            i["system_name"],
            i["env"],
            i["status_color"],
            i["cpu_level"],
            i["mem_level"],
            i["disk_level"],
            i["captured_at"],
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=monitoring_abnormal.csv"},
    )
