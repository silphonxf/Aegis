from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SelfcheckTemplateCreate(BaseModel):
    system_id: int
    check_type: Literal["daily", "weekly", "yearly"]
    name: str


class SelfcheckRecordCreate(BaseModel):
    system_id: int
    template_id: int
    result: Literal["normal", "warning", "critical"]
    summary: str | None = None
    checked_at: datetime
