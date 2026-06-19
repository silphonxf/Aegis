from typing import Optional

from pydantic import BaseModel, Field


class CaptureFetchRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1000)
    note: Optional[str] = Field(default=None, max_length=500)


class CaptureAnalyzeRequest(BaseModel):
    title: str = Field(default="抓包结果分析", min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=20000)
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    source: str = Field(default="manual_capture", min_length=1, max_length=64)
    note: Optional[str] = Field(default=None, max_length=500)
