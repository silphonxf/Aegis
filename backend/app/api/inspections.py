from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.inspection import InspectionPoint, InspectionRecord
from app.models.user import User
from app.schemas.inspection import InspectionCreate
from app.services.audit import log_action

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.get("/points/resolve")
def resolve_point_by_qr(qr_content: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    point = db.query(InspectionPoint).filter(InspectionPoint.qr_content == qr_content).first()
    if not point:
        raise HTTPException(status_code=404, detail="未找到对应巡检点")
    return {
        "point_id": point.id,
        "system_id": point.system_id,
        "point_code": point.point_code,
        "location": point.location,
    }


@router.post("/records")
def create_record(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("inspector", "admin", "super_admin")),
):
    rec = InspectionRecord(
        system_id=payload.system_id,
        point_id=payload.point_id,
        inspector_id=current_user.id,
        result=payload.result,
        note=payload.note,
        inspected_at=payload.inspected_at,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    log_action(db, "create_inspection_record", "inspection_record", current_user, {"record_id": rec.id})
    return {"id": rec.id}


@router.get("/records")
def list_records(
    system_id: int | None = None,
    result: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)

    q = db.query(InspectionRecord)
    if system_id is not None:
        q = q.filter(InspectionRecord.system_id == system_id)
    if result:
        q = q.filter(InspectionRecord.result == result)
    if start_at:
        q = q.filter(InspectionRecord.inspected_at >= start_at)
    if end_at:
        q = q.filter(InspectionRecord.inspected_at <= end_at)

    total = q.count()
    items = q.order_by(InspectionRecord.inspected_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id": i.id,
                "system_id": i.system_id,
                "point_id": i.point_id,
                "inspector_id": i.inspector_id,
                "result": i.result,
                "note": i.note,
                "inspected_at": i.inspected_at,
            }
            for i in items
        ],
    }
