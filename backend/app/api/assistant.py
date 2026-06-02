from fastapi import APIRouter

from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse, AssistantConfirmRequest
from app.services.assistant import AssistantExecutor

router = APIRouter(prefix="/assistant", tags=["assistant"])
executor = AssistantExecutor()


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(payload: AssistantChatRequest):
    return executor.chat(payload.conversation_id, payload.message, payload.attachments)


@router.post("/confirm", response_model=AssistantChatResponse)
def assistant_confirm(payload: AssistantConfirmRequest):
    return executor.confirm(payload.conversation_id, payload.action_id, payload.confirmed)
