from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.rule import StatusRule
from app.models.system import System, SystemLogConfig, SystemStatusSnapshot, SystemUserBinding
from app.models.user import User
from app.schemas.system import StatusSnapshotCreate
from app.services.audit import log_action

router = APIRouter(prefix="/systems", tags=["systems"])


def _visible_system_query(db: Session, user: User):
    q = db.query(System).filter(System.is_active.is_(True))
    if user.role.code in {"admin", "super_admin"}:
        return q
    return q.join(SystemUserBinding, SystemUserBinding.system_id == System.id).filter(
        SystemUserBinding.binding_role == "owner",
        SystemUserBinding.user_id == user.id,
    )


def _normalize_metric(value: Optional[int], warn: int, critical: int) -> str:
    if value is None:
        return "unknown"
    if value >= critical:
        return "critical"
    if value >= warn:
        return "warning"
    return "normal"


def _calc_color(levels: List[str], host_online: str, port_ok: str, last_inspection_result: str, last_selfcheck_result: str) -> str:
    if host_online == "abnormal" or port_ok == "abnormal":
        return "red"
    if last_inspection_result == "abnormal" or last_selfcheck_result == "critical":
        return "red"
    if "critical" in levels:
        return "red"
    if last_selfcheck_result == "warning" or "warning" in levels:
        return "yellow"
    return "green"


@router.get("/accessible")
def list_accessible_systems(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    systems = _visible_system_query(db, current_user).order_by(System.id.asc()).all()
    return {
        "items": [
            {
                "system_id": s.id,
                "system_code": s.system_code,
                "system_name": s.name,
                "host_address": s.host_address,
                "env": s.env,
                "selfcheck_skill": getattr(s, "selfcheck_skill", None),
            }
            for s in systems
        ]
    }


@router.get("/accessible-log-configs")
def list_accessible_system_log_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    systems = _visible_system_query(db, current_user).order_by(System.id.asc()).all()
    system_ids = [item.id for item in systems]
    log_rows = (
        db.query(SystemLogConfig)
        .filter(SystemLogConfig.system_id.in_(system_ids), SystemLogConfig.is_active.is_(True))
        .order_by(SystemLogConfig.system_id.asc(), SystemLogConfig.id.asc())
        .all()
        if system_ids else []
    )
    logs_by_system: Dict[int, List[SystemLogConfig]] = {}
    for row in log_rows:
        logs_by_system.setdefault(row.system_id, []).append(row)

    return {
        "items": [
            {
                "system_id": s.id,
                "system_code": s.system_code,
                "system_name": s.name,
                "host_address": s.host_address,
                "env": s.env,
                "selfcheck_skill": getattr(s, "selfcheck_skill", None),
                "log_configs": [
                    {
                        "id": item.id,
                        "log_name": item.log_name,
                        "absolute_path": item.absolute_path,
                        "log_level": item.log_level,
                        "remark": item.remark,
                    }
                    for item in logs_by_system.get(s.id, [])
                ],
            }
            for s in systems
        ]
    }


@router.get("/{system_id}/log-configs")
def list_system_log_configs(system_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    system = _visible_system_query(db, current_user).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail={"code": "SYSTEM_NOT_FOUND", "message": "系统不存在或无权访问"})
    rows = (
        db.query(SystemLogConfig)
        .filter(SystemLogConfig.system_id == system_id, SystemLogConfig.is_active.is_(True))
        .order_by(SystemLogConfig.id.asc())
        .all()
    )
    return {
        "system_id": system.id,
        "system_name": system.name,
        "host_address": system.host_address,
        "items": [
            {
                "id": item.id,
                "log_name": item.log_name,
                "absolute_path": item.absolute_path,
                "log_level": item.log_level,
                "remark": item.remark,
            }
            for item in rows
        ],
    }


@router.get("/status/overview")
def status_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    systems = _visible_system_query(db, current_user).all()
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
        cpu_usage=payload.cpu_usage,
        mem_usage=payload.mem_usage,
        disk_usage=payload.disk_usage,
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
        "cpu_usage": payload.cpu_usage,
        "mem_usage": payload.mem_usage,
        "disk_usage": payload.disk_usage,
        "cpu_level": cpu_level,
        "mem_level": mem_level,
        "disk_level": disk_level,
    }
