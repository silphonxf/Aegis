from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.schemas.assistant import AssistantAction, AssistantChatResponse, AssistantToolCall


def build_response(
    conversation_id: str,
    reply: str,
    *,
    intent: Optional[str] = None,
    tool_calls: Optional[List[AssistantToolCall]] = None,
    actions: Optional[List[AssistantAction]] = None,
    cards: Optional[List[Dict[str, Any]]] = None,
    data: Optional[Dict[str, Any]] = None,
    requires_confirmation: bool = False,
    pending_action: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> AssistantChatResponse:
    return AssistantChatResponse(
        conversation_id=conversation_id,
        reply=reply,
        intent=intent,
        tool_calls=tool_calls or [],
        actions=actions or [],
        cards=cards or [],
        data=data or {},
        requires_confirmation=requires_confirmation,
        pending_action=pending_action,
        context=context or {},
    )
