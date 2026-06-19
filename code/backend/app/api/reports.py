from typing import Any, Dict, List, Optional, Set, Tuple
import csv
from datetime import datetime
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.inspection import InspectionRecord
from app.models.selfcheck import ChecklistTemplate, SelfcheckRecord
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/inspections")
def inspection_report(
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
        "items": [{"id": i.id, "system_id": i.system_id, "result": i.result, "inspected_at": i.inspected_at} for i in items],
    }


@router.get("/selfchecks")
def selfcheck_report(
    system_id: Optional[int] = None,
    check_type: Optional[str] = None,
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

    q = db.query(SelfcheckRecord)
    if check_type:
        q = q.join(ChecklistTemplate, ChecklistTemplate.id == SelfcheckRecord.template_id).filter(
            ChecklistTemplate.check_type == check_type
        )
    if system_id is not None:
        q = q.filter(SelfcheckRecord.system_id == system_id)
    if result:
        q = q.filter(SelfcheckRecord.result == result)
    if start_at:
        q = q.filter(SelfcheckRecord.checked_at >= start_at)
    if end_at:
        q = q.filter(SelfcheckRecord.checked_at <= end_at)

    total = q.count()
    items = q.order_by(SelfcheckRecord.checked_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [{"id": i.id, "system_id": i.system_id, "result": i.result, "checked_at": i.checked_at} for i in items],
    }


@router.get("/inspections/export")
def inspection_export(
    system_id: Optional[int] = None,
    result: Optional[str] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(InspectionRecord)
    if system_id is not None:
        q = q.filter(InspectionRecord.system_id == system_id)
    if result:
        q = q.filter(InspectionRecord.result == result)
    if start_at:
        q = q.filter(InspectionRecord.inspected_at >= start_at)
    if end_at:
        q = q.filter(InspectionRecord.inspected_at <= end_at)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "system_id", "point_id", "inspector_id", "result", "note", "inspected_at"])
    for i in q.order_by(InspectionRecord.inspected_at.desc()).all():
        writer.writerow([i.id, i.system_id, i.point_id, i.inspector_id, i.result, i.note or "", i.inspected_at])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=inspections.csv"})


@router.get("/selfchecks/export")
def selfcheck_export(
    system_id: Optional[int] = None,
    check_type: Optional[str] = None,
    result: Optional[str] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(SelfcheckRecord)
    if check_type:
        q = q.join(ChecklistTemplate, ChecklistTemplate.id == SelfcheckRecord.template_id).filter(
            ChecklistTemplate.check_type == check_type
        )
    if system_id is not None:
        q = q.filter(SelfcheckRecord.system_id == system_id)
    if result:
        q = q.filter(SelfcheckRecord.result == result)
    if start_at:
        q = q.filter(SelfcheckRecord.checked_at >= start_at)
    if end_at:
        q = q.filter(SelfcheckRecord.checked_at <= end_at)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "system_id", "template_id", "operator_id", "result", "summary", "checked_at"])
    for i in q.order_by(SelfcheckRecord.checked_at.desc()).all():
        writer.writerow([i.id, i.system_id, i.template_id, i.operator_id, i.result, i.summary or "", i.checked_at])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=selfchecks.csv"})
