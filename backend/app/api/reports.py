import csv
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.inspection import InspectionRecord
from app.models.selfcheck import SelfcheckRecord
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/inspections")
def inspection_report(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = db.query(InspectionRecord).order_by(InspectionRecord.inspected_at.desc()).limit(500).all()
    return {"items": [{"id": i.id, "system_id": i.system_id, "result": i.result, "inspected_at": i.inspected_at} for i in items]}


@router.get("/selfchecks")
def selfcheck_report(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = db.query(SelfcheckRecord).order_by(SelfcheckRecord.checked_at.desc()).limit(500).all()
    return {"items": [{"id": i.id, "system_id": i.system_id, "result": i.result, "checked_at": i.checked_at} for i in items]}


@router.get("/inspections/export")
def inspection_export(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "system_id", "point_id", "inspector_id", "result", "note", "inspected_at"])
    for i in db.query(InspectionRecord).order_by(InspectionRecord.inspected_at.desc()).all():
        writer.writerow([i.id, i.system_id, i.point_id, i.inspector_id, i.result, i.note or "", i.inspected_at])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=inspections.csv"})


@router.get("/selfchecks/export")
def selfcheck_export(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "system_id", "template_id", "operator_id", "result", "summary", "checked_at"])
    for i in db.query(SelfcheckRecord).order_by(SelfcheckRecord.checked_at.desc()).all():
        writer.writerow([i.id, i.system_id, i.template_id, i.operator_id, i.result, i.summary or "", i.checked_at])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=selfchecks.csv"})
