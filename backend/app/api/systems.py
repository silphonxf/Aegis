from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.system import System, SystemStatusSnapshot
from app.models.user import User

router = APIRouter(prefix="/systems", tags=["systems"])


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
    status_color: str = "green",
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    snap = SystemStatusSnapshot(system_id=system_id, status_color=status_color)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return {"id": snap.id, "system_id": system_id, "saved": True}
