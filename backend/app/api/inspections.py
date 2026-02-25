from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/inspections", tags=["inspections"])


class InspectionCreate(BaseModel):
    system_id: int
    point_id: int
    result: Literal["normal", "abnormal"]
    note: str | None = None
    inspected_at: datetime


@router.post("/records")
def create_record(payload: InspectionCreate):
    # TODO: 持久化到DM数据库
    return {"id": 1, **payload.model_dump(mode="json")}


@router.get("/records")
def list_records(system_id: int | None = None):
    return {"items": [], "system_id": system_id}
