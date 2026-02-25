from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InspectionCreate(BaseModel):
    system_id: int
    point_id: int
    result: Literal["normal", "abnormal"]
    note: str | None = None
    inspected_at: datetime
