from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel


class SelfcheckTemplateCreate(BaseModel):
    system_id: int
    check_type: Literal["daily", "weekly", "yearly"]
    name: str


class SelfcheckRecordCreate(BaseModel):
    system_id: int
    template_id: int
    result: Literal["normal", "warning", "critical"]
    summary: Optional[str] = None
    review_status: Optional[Literal["pending", "reviewed"]] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    checked_at: datetime


class SelfcheckRecordSimpleCreate(BaseModel):
    content: str
    result: Literal["normal", "critical"]
    note: Optional[str] = None
    system_id: Optional[int] = None
