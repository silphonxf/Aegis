from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel


class InspectionCreate(BaseModel):
    system_id: int
    point_id: int
    room_id: Optional[int] = None
    result: Literal["normal", "abnormal"]
    note: Optional[str] = None
    source: Optional[str] = None
    inspected_at: datetime
