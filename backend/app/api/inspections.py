from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.inspection import InspectionPoint, InspectionRecord
from app.models.system import System
from app.models.user import User
from app.schemas.inspection import InspectionCreate
from app.services.audit import log_action

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.get("/points/resolve")
def resolve_point_by_qr(qr_content: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    qr_text = (qr_content or "").strip()

    # 新逻辑：二维码为系统ID（纯数字）时，按 system_id 定位系统与巡检点
    if qr_text.isdigit():
        system_id = int(qr_text)
        system = db.query(System).filter(System.id == system_id).first()
        if not system:
            raise HTTPException(status_code=404, detail="找不到巡检点")

        point = (
            db.query(InspectionPoint)
            .filter(InspectionPoint.system_id == system_id)
            .order_by(InspectionPoint.id.asc())
            .first()
        )
        if not point:
            raise HTTPException(status_code=404, detail="找不到巡检点")

        point_name = point.location or point.point_code
        return {
            "point_id": point.id,
            "system_id": point.system_id,
            "system_name": system.name,
            "point_code": point.point_code,
            "point_name": point_name,
            "location": point.location,
        }

    # 兼容旧逻辑：二维码为完整 qr_content
    point = db.query(InspectionPoint).filter(InspectionPoint.qr_content == qr_text).first()
    if not point:
        raise HTTPException(status_code=404, detail="未找到对应巡检点")

    system = db.query(System).filter(System.id == point.system_id).first()
    point_name = point.location or point.point_code
    return {
        "point_id": point.id,
        "system_id": point.system_id,
        "system_name": system.name if system else "",
        "point_code": point.point_code,
        "point_name": point_name,
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
    system_id: Optional[int] = None,
    result: Optional[str] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
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
