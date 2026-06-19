from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AIConversationCreateRequest(BaseModel):
    title: str = Field(default="新会话", min_length=1, max_length=120)
    source: str = Field(default="mobile", min_length=1, max_length=32)


class AIConversationItem(BaseModel):
    conversation_id: str
    title: str
    source: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: Optional[str] = None


class AIConversationDetail(AIConversationItem):
    messages: List[dict] = Field(default_factory=list)
    attachments: List[dict] = Field(default_factory=list)
    message_count: int = 0
    attachment_count: int = 0


class AIConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AIConversationListResponse(BaseModel):
    items: List[AIConversationItem] = Field(default_factory=list)
    total: int = 0
