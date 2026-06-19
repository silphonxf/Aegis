from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.emergency_config import EmergencyActionExecuteRequest
from app.services.audit import log_action
from app.services.emergency_config import create_emergency_task, list_mobile_emergency_actions

router = APIRouter(prefix="/emergency", tags=["emergency"])


@router.get("/actions")
def list_emergency_actions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_mobile_emergency_actions(db, current_user)


@router.post("/actions/execute")
def execute_emergency_action(
    payload: EmergencyActionExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = create_emergency_task(db, current_user, payload.action_code)
    log_action(db, "create_emergency_task", "emergency", current_user, result)
    return result
