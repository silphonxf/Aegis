from typing import Optional
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.ai_chat_file import AIChatFile
from app.models.ai_chat_message import AIChatMessage
from app.models.ai_diagnosis import AIDiagnosis
from app.models.offline_analysis import OfflineAnalysisResult, OfflineAnalysisTask
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponse, ChatV2Request, DiagnoseRequest
from app.schemas.offline_ai import OfflineAnalyzeRequest
from app.services.ai_provider import run_chat, run_diagnose, run_offline_analyze
from app.services.audit import log_action

router = APIRouter(prefix="/ai", tags=["ai"])


def _build_chat_attachment_notes(attachments: list[dict]) -> list[str]:
    notes: list[str] = []
    for item in attachments:
        name = str(item.get("name") or "未命名附件")
        kind = str(item.get("type") or "unknown")
        size = int(item.get("size") or 0)
        size_text = f"{round(size / 1024, 1)}KB" if size >= 1024 else f"{size}B"
        notes.append(f"已收到附件：{name}（{kind}，{size_text}）")
    return notes


def _load_chat_files(db: Session, file_refs: list[dict]) -> list[dict]:
    items: list[dict] = []
    for ref in file_refs:
        row = db.query(AIChatFile).filter(AIChatFile.id == ref.get("file_id")).first()
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



def _load_conversation_history(db: Session, conversation_id: str | None) -> list[dict]:
    if not conversation_id:
        return []
    rows = (
        db.query(AIChatMessage)
        .filter(AIChatMessage.conversation_id == conversation_id)
        .order_by(AIChatMessage.created_at.desc(), AIChatMessage.id.desc())
        .limit(6)
        .all()
    )
    rows.reverse()
    return [{"role": row.role, "content": row.content[:800]} for row in rows]



def _save_conversation_turn(db: Session, conversation_id: str | None, user_message: str, ai_reply: str) -> None:
    if not conversation_id:
        return
    if user_message.strip():
        db.add(AIChatMessage(conversation_id=conversation_id, role="user", content=user_message.strip()))
    if ai_reply.strip():
        db.add(AIChatMessage(conversation_id=conversation_id, role="assistant", content=ai_reply.strip()))


@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    message = (payload.message or "").strip()
    if not message and not payload.attachments:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_CHAT", "message": "消息和附件不能同时为空"})

    history = _load_conversation_history(db, payload.conversation_id)
    result = run_chat(payload, history=history)
    detail_parts = []
    if message:
        detail_parts.append(f"用户问题：{message}")
    attachment_notes = _build_chat_attachment_notes([item.dict() for item in payload.attachments])
    if attachment_notes:
        detail_parts.append("附件概览：\n" + "\n".join(f"- {item}" for item in attachment_notes))

    row = AIDiagnosis(
        title=message[:120] or "移动端 AI 问答",
        severity=result.get("severity", "medium"),
        detail="\n\n".join(detail_parts)[:2000] or "移动端 AI 问答",
        suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
    )
    conversation_id = payload.conversation_id or f"chat-{row.id}"
    db.add(row)
    _save_conversation_turn(db, conversation_id, message, result.get("reply", ""))
    db.commit()
    db.refresh(row)

    log_action(
        db,
        "ai_chat",
        "ai",
        current_user,
        {
            "diagnosis_id": row.id,
            "severity": result.get("severity", "medium"),
            "mode": result.get("mode"),
            "elapsed_ms": result.get("elapsed_ms"),
            "fallback_reason": result.get("fallback_reason"),
            "attachment_count": len(payload.attachments),
        },
    )

    return ChatResponse(
        conversation_id=result.get("conversation_id") or payload.conversation_id or f"chat-{row.id}",
        mode=result.get("mode", "rule_fallback"),
        summary=result.get("summary", ""),
        reply=result.get("reply", ""),
        severity=result.get("severity", "medium"),
        suggestions=result.get("suggestions", []),
        attachment_notes=result.get("attachment_notes", []),
        elapsed_ms=result.get("elapsed_ms", 0),
        fallback_reason=result.get("fallback_reason"),
    )


@router.post("/chat/v2", response_model=ChatResponse)
def chat_with_ai_v2(
    payload: ChatV2Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    message = (payload.message or "").strip()
    file_refs = [item.dict() for item in payload.attachments]
    attachments = _load_chat_files(db, file_refs)
    if not message and not attachments:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_CHAT", "message": "消息和附件不能同时为空"})

    enriched_message = message
    if attachments:
        attachment_blocks = []
        for item in attachments:
            excerpt = (item.get("extracted_text") or "")[:600]
            if excerpt:
                attachment_blocks.append(f"附件 {item['name']} 内容摘录：\n{excerpt}")
            else:
                attachment_blocks.append(f"附件 {item['name']}（{item['type']}，{item['size']} bytes）")
        enriched_message = (message + "\n\n" + "\n\n".join(attachment_blocks)).strip()

    chat_payload = ChatRequest(
        message=enriched_message,
        conversation_id=payload.conversation_id,
        attachments=[],
    )
    history = _load_conversation_history(db, payload.conversation_id)
    result = run_chat(chat_payload, history=history)

    attachment_notes = _build_chat_attachment_notes(attachments)
    detail_parts = []
    if message:
        detail_parts.append(f"用户问题：{message}")
    if attachment_notes:
        detail_parts.append("附件概览：\n" + "\n".join(f"- {item}" for item in attachment_notes))

    row = AIDiagnosis(
        title=message[:120] or "移动端 AI 问答",
        severity=result.get("severity", "medium"),
        detail="\n\n".join(detail_parts)[:2000] or "移动端 AI 问答",
        suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
    )
    conversation_id = payload.conversation_id or f"chat-{row.id}"
    db.add(row)
    _save_conversation_turn(db, conversation_id, message, result.get("reply", ""))
    db.commit()
    db.refresh(row)

    log_action(
        db,
        "ai_chat_v2",
        "ai",
        current_user,
        {
            "diagnosis_id": row.id,
            "severity": result.get("severity", "medium"),
            "mode": result.get("mode"),
            "elapsed_ms": result.get("elapsed_ms"),
            "fallback_reason": result.get("fallback_reason"),
            "attachment_count": len(attachments),
        },
    )

    return ChatResponse(
        conversation_id=result.get("conversation_id") or payload.conversation_id or f"chat-{row.id}",
        mode=result.get("mode", "rule_fallback"),
        summary=result.get("summary", ""),
        reply=result.get("reply", ""),
        severity=result.get("severity", "medium"),
        suggestions=result.get("suggestions", []),
        attachment_notes=attachment_notes,
        elapsed_ms=result.get("elapsed_ms", 0),
        fallback_reason=result.get("fallback_reason"),
    )


@router.post("/diagnose")
def diagnose(
    payload: DiagnoseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    result = run_diagnose(payload.title, payload.detail, payload.severity)

    row = AIDiagnosis(
        title=payload.title,
        severity=result.get("severity", payload.severity),
        detail=payload.detail,
        suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db,
        "ai_diagnose",
        "ai",
        current_user,
        {
            "diagnosis_id": row.id,
            "severity": result.get("severity", payload.severity),
            "mode": result.get("mode"),
            "elapsed_ms": result.get("elapsed_ms"),
            "fallback_reason": result.get("fallback_reason"),
        },
    )
    return {
        "id": row.id,
        "mode": result.get("mode", "rule_fallback"),
        "title": payload.title,
        "severity": result.get("severity", payload.severity),
        "summary": result.get("summary", ""),
        "suggestions": result.get("suggestions", []),
        "elapsed_ms": result.get("elapsed_ms", 0),
        "fallback_reason": result.get("fallback_reason"),
    }


@router.get("/diagnoses")
def list_diagnoses(
    page: int = 1,
    size: int = 20,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)

    q = db.query(AIDiagnosis)
    if severity:
        q = q.filter(AIDiagnosis.severity == severity)

    total = q.count()
    items = q.order_by(AIDiagnosis.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return {
        "page": page,
        "size": size,
        "total": total,
        "filters": {"severity": severity},
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity,
                "detail": i.detail,
                "suggestions": json.loads(i.suggestions),
                "created_at": i.created_at,
            }
            for i in items
        ],
    }


@router.post("/offline/analyze")
def offline_analyze(
    payload: OfflineAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    result = run_offline_analyze(payload)

    task = OfflineAnalysisTask(
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        status="done",
        severity=result.get("severity", payload.severity),
        title=payload.title,
        summary=result.get("summary", ""),
        created_by=current_user.username,
    )
    db.add(task)
    db.flush()

    analysis_result = OfflineAnalysisResult(
        task_id=task.id,
        matched_rules=json.dumps(result.get("matched_rules", []), ensure_ascii=False),
        suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
        raw_excerpt=result.get("excerpt", ""),
    )
    db.add(analysis_result)
    db.commit()

    log_action(
        db,
        "ai_offline_analyze",
        "ai_offline",
        current_user,
        {
            "task_id": task.id,
            "severity": result.get("severity", payload.severity),
            "mode": result.get("mode"),
            "elapsed_ms": result.get("elapsed_ms"),
            "fallback_reason": result.get("fallback_reason"),
        },
    )
    return {
        "task_id": task.id,
        "status": task.status,
        "mode": result.get("mode", "rule_fallback"),
        "severity": result.get("severity", payload.severity),
        "summary": result.get("summary", ""),
        "matched_rules": result.get("matched_rules", []),
        "suggestions": result.get("suggestions", []),
        "elapsed_ms": result.get("elapsed_ms", 0),
        "fallback_reason": result.get("fallback_reason"),
    }


@router.get("/offline/tasks")
def list_offline_tasks(
    page: int = 1,
    size: int = 20,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    page = max(page, 1)
    size = min(max(size, 1), 100)

    q = db.query(OfflineAnalysisTask)
    if severity:
        q = q.filter(OfflineAnalysisTask.severity == severity)

    total = q.count()
    items = q.order_by(OfflineAnalysisTask.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "source_type": t.source_type,
                "source_ref": t.source_ref,
                "status": t.status,
                "severity": t.severity,
                "summary": t.summary,
                "created_by": t.created_by,
                "created_at": t.created_at,
            }
            for t in items
        ],
    }


@router.get("/offline/tasks/{task_id}")
def get_offline_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "super_admin")),
):
    task = db.query(OfflineAnalysisTask).filter(OfflineAnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})

    result = db.query(OfflineAnalysisResult).filter(OfflineAnalysisResult.task_id == task_id).order_by(OfflineAnalysisResult.id.desc()).first()
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "source_type": task.source_type,
            "source_ref": task.source_ref,
            "status": task.status,
            "severity": task.severity,
            "summary": task.summary,
            "created_by": task.created_by,
            "created_at": task.created_at,
        },
        "result": {
            "matched_rules": json.loads(result.matched_rules) if result else [],
            "suggestions": json.loads(result.suggestions) if result else [],
            "raw_excerpt": result.raw_excerpt if result else "",
            "created_at": result.created_at if result else None,
        },
    }
