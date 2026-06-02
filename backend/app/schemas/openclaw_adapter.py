from typing import List, Optional

from pydantic import BaseModel, Field


class AdapterContext(BaseModel):
    source: Optional[str] = Field(default=None, max_length=64)
    module: Optional[str] = Field(default=None, max_length=64)
    user: Optional[str] = Field(default=None, max_length=64)


class AdapterAttachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(default="application/octet-stream", min_length=1, max_length=120)
    size: int = Field(default=0, ge=0)
    data_url: Optional[str] = Field(default=None, max_length=6000000)


class AdapterChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    message: str = Field(default="", max_length=4000)
    attachments: List[AdapterAttachment] = Field(default_factory=list, max_items=8)
    context: Optional[AdapterContext] = None


class AdapterDiagnoseRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=20000)
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    context: Optional[AdapterContext] = None


class AdapterLogAnalyzeRequest(BaseModel):
    title: str = Field(default="离线错误日志分析", min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=20000)
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    source_type: str = Field(default="manual", pattern="^(manual|system)$")
    source_ref: Optional[str] = Field(default=None, max_length=255)
    context: Optional[AdapterContext] = None
