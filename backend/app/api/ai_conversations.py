from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.ai_chat_file import AIChatFile
from app.models.ai_chat_message import AIChatMessage
from app.models.ai_conversation import AIConversation
from app.models.user import User
from app.schemas.ai_conversation import (
    AIConversationCreateRequest,
    AIConversationDetail,
    AIConversationItem,
    AIConversationListResponse,
    AIConversationRenameRequest,
)
from app.services.audit import log_action

router = APIRouter(prefix="/ai/conversations", tags=["ai-conversations"])


@router.post("", response_model=AIConversationItem)
def create_conversation(
    payload: AIConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    conversation_id = f"mobile-ai-chat-{int(datetime.utcnow().timestamp() * 1000)}"
    row = AIConversation(
        conversation_id=conversation_id,
        title=payload.title.strip() or "新会话",
        source=payload.source.strip() or "mobile",
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_action(db, "ai_conversation_create", "ai", current_user, {"conversation_id": row.conversation_id})
    return AIConversationItem(
        conversation_id=row.conversation_id,
        title=row.title,
        source=row.source,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=AIConversationListResponse)
def list_conversations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    rows = db.query(AIConversation).order_by(AIConversation.updated_at.desc(), AIConversation.id.desc()).limit(20).all()
    return AIConversationListResponse(
        items=[
            AIConversationItem(
                conversation_id=row.conversation_id,
                title=row.title,
                source=row.source,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ],
        total=len(rows),
    )


@router.get("/{conversation_id}", response_model=AIConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    row = db.query(AIConversation).filter(AIConversation.conversation_id == conversation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "CONVERSATION_NOT_FOUND", "message": "会话不存在"})

    messages = db.query(AIChatMessage).filter(AIChatMessage.conversation_id == conversation_id).order_by(AIChatMessage.created_at.desc(), AIChatMessage.id.desc()).limit(20).all()
    attachments = db.query(AIChatFile).filter(AIChatFile.conversation_id == conversation_id).order_by(AIChatFile.created_at.desc(), AIChatFile.id.desc()).limit(12).all()
    messages.reverse()
    attachments.reverse()

    return AIConversationDetail(
        conversation_id=row.conversation_id,
        title=row.title,
        source=row.source,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        messages=[{"role": item.role, "content": item.content, "created_at": item.created_at} for item in messages],
        attachments=[{"file_id": item.id, "name": item.original_name, "type": item.mime_type, "size": item.size_bytes, "created_at": item.created_at} for item in attachments],
        message_count=len(messages),
        attachment_count=len(attachments),
    )


def _touch_conversation(db: Session, conversation_id: str, *, title_hint: str | None = None) -> None:
    row = db.query(AIConversation).filter(AIConversation.conversation_id == conversation_id).first()
    if not row:
        return
    if title_hint and row.title.strip() in {"", "新会话"}:
        row.title = title_hint.strip()[:120] or row.title
    row.updated_at = datetime.utcnow()


@router.put("/{conversation_id}", response_model=AIConversationItem)
def rename_conversation(
    conversation_id: str,
    payload: AIConversationRenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    row = db.query(AIConversation).filter(AIConversation.conversation_id == conversation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "CONVERSATION_NOT_FOUND", "message": "会话不存在"})
    row.title = payload.title.strip()
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    log_action(db, "ai_conversation_rename", "ai", current_user, {"conversation_id": row.conversation_id, "title": row.title})
    return AIConversationItem(
        conversation_id=row.conversation_id,
        title=row.title,
        source=row.source,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
