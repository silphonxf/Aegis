from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ai_external_key import AIExternalApiKey
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse, AssistantConfirmRequest, ExternalAssistantChatRequest
from app.services.audit import log_action
from app.services.assistant import AssistantExecutor

router = APIRouter(prefix="/assistant", tags=["assistant"])
executor = AssistantExecutor()


def _hash_external_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_external_api_key(db: Session, api_key: str) -> AIExternalApiKey:
    row = db.query(AIExternalApiKey).filter(AIExternalApiKey.key_hash == _hash_external_api_key(api_key)).first()
    if not row or not row.is_active:
        raise HTTPException(status_code=401, detail={"code": "AI_EXTERNAL_KEY_INVALID", "message": "apikey 无效或已停用"})
    row.last_used_at = datetime.utcnow()
    db.commit()
    return row


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(payload: AssistantChatRequest, _: User = Depends(get_current_user)):
    return executor.chat(payload.conversation_id, payload.message, payload.attachments)


@router.post("/confirm", response_model=AssistantChatResponse)
def assistant_confirm(payload: AssistantConfirmRequest, _: User = Depends(get_current_user)):
    return executor.confirm(payload.conversation_id, payload.action_id, payload.confirmed)


@router.post("/external/chat", response_model=AssistantChatResponse)
def assistant_external_chat(payload: ExternalAssistantChatRequest, db: Session = Depends(get_db)):
    key = _validate_external_api_key(db, payload.apikey)
    result = executor.chat(payload.conversation_id, payload.message, payload.attachments)
    log_action(
        db,
        "ai_external_chat",
        "ai_external_key",
        detail={"key_id": key.id, "key_prefix": key.key_prefix, "conversation_id": result.conversation_id},
        username=f"external:{key.name}",
    )
    return result
