from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/selfchecks", tags=["selfchecks"])


class SelfCheckRecordCreate(BaseModel):
    system_id: int
    template_id: int
    result: Literal["normal", "warning", "critical"]
    summary: str | None = None
    checked_at: datetime


@router.get("/templates")
def list_templates():
    return {"items": []}


@router.post("/records")
def create_selfcheck_record(payload: SelfCheckRecordCreate):
    return {"id": 1, **payload.model_dump(mode="json")}


@router.get("/records")
def list_selfcheck_records(system_id: int | None = None):
    return {"items": [], "system_id": system_id}
