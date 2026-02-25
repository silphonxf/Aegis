from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.selfcheck import ChecklistTemplate, SelfcheckRecord
from app.models.user import User
from app.schemas.selfcheck import SelfcheckRecordCreate, SelfcheckTemplateCreate

router = APIRouter(prefix="/selfchecks", tags=["selfchecks"])


@router.get("/templates")
def list_templates(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = db.query(ChecklistTemplate).filter(ChecklistTemplate.is_active.is_(True)).all()
    return {"items": [{"id": i.id, "system_id": i.system_id, "check_type": i.check_type, "name": i.name} for i in items]}


@router.post("/templates")
def create_template(
    payload: SelfcheckTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    t = ChecklistTemplate(system_id=payload.system_id, check_type=payload.check_type, name=payload.name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id}


@router.post("/records")
def create_selfcheck_record(
    payload: SelfcheckRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    r = SelfcheckRecord(
        system_id=payload.system_id,
        template_id=payload.template_id,
        operator_id=current_user.id,
        result=payload.result,
        summary=payload.summary,
        checked_at=payload.checked_at,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id}


@router.get("/records")
def list_selfcheck_records(
    system_id: int | None = None,
    result: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(SelfcheckRecord)
    if system_id is not None:
        q = q.filter(SelfcheckRecord.system_id == system_id)
    if result:
        q = q.filter(SelfcheckRecord.result == result)
    if start_at:
        q = q.filter(SelfcheckRecord.checked_at >= start_at)
    if end_at:
        q = q.filter(SelfcheckRecord.checked_at <= end_at)
    items = q.order_by(SelfcheckRecord.checked_at.desc()).limit(200).all()
    return {"items": [
        {
            "id": i.id,
            "system_id": i.system_id,
            "template_id": i.template_id,
            "operator_id": i.operator_id,
            "result": i.result,
            "summary": i.summary,
            "checked_at": i.checked_at,
        }
        for i in items
    ]}
