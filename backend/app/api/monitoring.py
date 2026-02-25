from fastapi import APIRouter, Depends
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.rule import StatusRule
from app.models.system import System, SystemStatusSnapshot
from app.models.user import User
from app.schemas.rule import StatusRuleUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


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

    return {"summary": summary, "items": items, "abnormal_items": abnormal[:20]}
