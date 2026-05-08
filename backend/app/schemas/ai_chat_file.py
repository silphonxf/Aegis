from typing import List, Optional

from pydantic import BaseModel, Field


class AIChatFileUploadRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(default="application/octet-stream", min_length=1, max_length=120)
    size: int = Field(default=0, ge=0)
    data_url: str = Field(min_length=1, max_length=6000000)


class AIChatFileItem(BaseModel):
    file_id: int
    name: str
    type: str
    size: int
    extracted_text: Optional[str] = None
    preview_excerpt: Optional[str] = None


class AIChatFileUploadResponse(BaseModel):
    ok: bool = True
    file: AIChatFileItem


class AIChatFileRef(BaseModel):
    file_id: int
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(default="application/octet-stream", min_length=1, max_length=120)
    size: int = Field(default=0, ge=0)


class AIChatV2Request(BaseModel):
    message: str = Field(default="", max_length=4000)
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    attachments: List[AIChatFileRef] = Field(default_factory=list, max_items=8)
