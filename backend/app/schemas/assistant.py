from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


class AssistantAction(BaseModel):
    type: str
    label: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class AssistantToolCall(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class AssistantChatResponse(BaseModel):
    conversation_id: str
    reply: str
    intent: Optional[str] = None
    tool_calls: List[AssistantToolCall] = Field(default_factory=list)
    actions: List[AssistantAction] = Field(default_factory=list)
    cards: List[Dict[str, Any]] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    pending_action: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class AssistantConfirmRequest(BaseModel):
    conversation_id: str
    action_id: str
    confirmed: bool
