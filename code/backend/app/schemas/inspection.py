from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel


class InspectionCreate(BaseModel):
    system_id: Optional[int] = None
    point_id: int
    room_id: Optional[int] = None
    result: Literal["normal", "abnormal"]
    note: Optional[str] = None
    source: Optional[str] = None
    check_results: List[Dict[str, str]] = []
    monitoring_confirmation: Optional[str] = None
    inspected_at: datetime
