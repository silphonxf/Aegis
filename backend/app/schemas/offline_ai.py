from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field


class OfflineAnalyzeRequest(BaseModel):
    title: str = Field(default="离线错误日志分析", min_length=1, max_length=120)
    source_type: str = Field(default="manual", regex="^(manual|system)$")
    source_ref: Optional[str] = Field(default=None, max_length=255)
    severity: str = Field(default="medium", regex="^(low|medium|high)$")
    detail: str = Field(min_length=1, max_length=20000)


class OfflineAnalyzeResponse(BaseModel):
    task_id: int
    status: str
    severity: str
    summary: str
    matched_rules: List[dict]
    suggestions: List[str]
