from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ai_chat_file import AIChatFile
from app.models.ai_chat_message import AIChatMessage
from app.models.ai_conversation import AIConversation
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


def _load_assistant_attachments(db: Session, file_refs: list[dict]) -> list[dict]:
    items: list[dict] = []
    for ref in file_refs or []:
        file_id = ref.get("file_id")
        if not file_id:
            continue
        row = db.query(AIChatFile).filter(AIChatFile.id == file_id).first()
        if not row:
            continue
        items.append(
            {
                "file_id": row.id,
                "name": row.original_name,
                "type": row.mime_type,
                "size": row.size_bytes,
                "extracted_text": row.extracted_text,
            }
        )
    return items


def _save_assistant_turn(db: Session, conversation_id: str | None, user_message: str, assistant_reply: str) -> None:
    if not conversation_id:
        return
    message = (user_message or "").strip()
    reply = (assistant_reply or "").strip()
    if message:
        db.add(AIChatMessage(conversation_id=conversation_id, role="user", content=message))
    if reply:
        db.add(AIChatMessage(conversation_id=conversation_id, role="assistant", content=reply))

    row = db.query(AIConversation).filter(AIConversation.conversation_id == conversation_id).first()
    if row:
        if message and row.title.strip() in {"", "新会话"}:
            row.title = message[:40]
        row.updated_at = datetime.utcnow()
    db.commit()


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(payload: AssistantChatRequest, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attachments = _load_assistant_attachments(db, payload.attachments)
    result = executor.chat(payload.conversation_id, payload.message, attachments)
    _save_assistant_turn(db, result.conversation_id, payload.message, result.reply)
    return result


@router.post("/confirm", response_model=AssistantChatResponse)
def assistant_confirm(payload: AssistantConfirmRequest, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = executor.confirm(payload.conversation_id, payload.action_id, payload.confirmed)
    _save_assistant_turn(db, result.conversation_id, "", result.reply)
    return result


@router.post("/external/chat", response_model=AssistantChatResponse)
def assistant_external_chat(payload: ExternalAssistantChatRequest, db: Session = Depends(get_db)):
    key = _validate_external_api_key(db, payload.apikey)
    attachments = _load_assistant_attachments(db, payload.attachments)
    result = executor.chat(payload.conversation_id, payload.message, attachments)
    log_action(
        db,
        "ai_external_chat",
        "ai_external_key",
        detail={"key_id": key.id, "key_prefix": key.key_prefix, "conversation_id": result.conversation_id},
        username=f"external:{key.name}",
    )
    return result
