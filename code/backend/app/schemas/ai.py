from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.ai_chat_file import AIChatFileRef


class DiagnoseRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=20000)
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")


class ChatAttachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(default="application/octet-stream", min_length=1, max_length=120)
    size: int = Field(default=0, ge=0)
    data_url: Optional[str] = Field(default=None, max_length=6000000)


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=4000)
    attachments: List[ChatAttachment] = Field(default_factory=list, max_items=8)
    conversation_id: Optional[str] = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    conversation_id: str
    mode: str
    summary: str
    reply: str
    severity: str
    suggestions: List[str] = Field(default_factory=list)
    attachment_notes: List[str] = Field(default_factory=list)
    elapsed_ms: int
    fallback_reason: Optional[str] = None


class ChatV2Request(BaseModel):
    message: str = Field(default="", max_length=4000)
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    attachments: List[AIChatFileRef] = Field(default_factory=list, max_items=8)
