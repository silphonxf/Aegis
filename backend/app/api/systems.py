from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.rule import StatusRule
from app.models.system import System, SystemStatusSnapshot
from app.models.user import User
from app.schemas.system import StatusSnapshotCreate
from app.services.audit import log_action

router = APIRouter(prefix="/systems", tags=["systems"])


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


@router.get("/status/overview")
def status_overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    systems = db.query(System).all()
    items = []
    for s in systems:
        snap = (
            db.query(SystemStatusSnapshot)
            .filter(SystemStatusSnapshot.system_id == s.id)
            .order_by(SystemStatusSnapshot.captured_at.desc())
            .first()
        )
        color = snap.status_color if snap else "green"
        items.append({"system_id": s.id, "system_name": s.name, "status_color": color})

    summary = {
        "green": sum(1 for i in items if i["status_color"] == "green"),
        "yellow": sum(1 for i in items if i["status_color"] == "yellow"),
        "red": sum(1 for i in items if i["status_color"] == "red"),
    }
    return {"summary": summary, "items": items}


@router.post("/{system_id}/status/snapshot")
def create_status_snapshot(
    system_id: int,
    payload: StatusSnapshotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    rule = db.query(StatusRule).order_by(StatusRule.id.asc()).first()
    if not rule:
        rule = StatusRule()
        db.add(rule)
        db.commit()
        db.refresh(rule)

    cpu_level = _normalize_metric(payload.cpu_usage, rule.cpu_warn, rule.cpu_critical)
    mem_level = _normalize_metric(payload.mem_usage, rule.mem_warn, rule.mem_critical)
    disk_level = _normalize_metric(payload.disk_usage, rule.disk_warn, rule.disk_critical)

    status_color = _calc_color(
        [cpu_level, mem_level, disk_level],
        host_online=payload.host_online,
        port_ok=payload.port_ok,
        last_inspection_result=payload.last_inspection_result,
        last_selfcheck_result=payload.last_selfcheck_result,
    )

    snap = SystemStatusSnapshot(
        system_id=system_id,
        host_online=payload.host_online,
        port_ok=payload.port_ok,
        cpu_level=cpu_level,
        mem_level=mem_level,
        disk_level=disk_level,
        last_inspection_result=payload.last_inspection_result,
        last_selfcheck_result=payload.last_selfcheck_result,
        status_color=status_color,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    log_action(
        db,
        "create_status_snapshot",
        "system_status_snapshot",
        current_user,
        {
            "snapshot_id": snap.id,
            "system_id": system_id,
            "status_color": status_color,
            "cpu_level": cpu_level,
            "mem_level": mem_level,
            "disk_level": disk_level,
        },
    )
    return {
        "id": snap.id,
        "system_id": system_id,
        "saved": True,
        "status_color": status_color,
        "cpu_level": cpu_level,
        "mem_level": mem_level,
        "disk_level": disk_level,
    }
