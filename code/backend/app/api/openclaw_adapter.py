from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.schemas.openclaw_adapter import AdapterChatRequest, AdapterDiagnoseRequest, AdapterLogAnalyzeRequest
from app.services.ai_provider import mock_diagnose, mock_suggestions, offline_rule_analyze

router = APIRouter(prefix="/aegis/ai", tags=["openclaw-adapter"])


def _check_auth(authorization: Optional[str]) -> None:
    if not settings.OPENCLAW_ADAPTER_ENABLED:
        raise HTTPException(status_code=404, detail={"code": "ADAPTER_DISABLED", "message": "OpenClaw adapter 未启用"})
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "缺少 Authorization Bearer token"})
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.OPENCLAW_ADAPTER_TOKEN:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "OpenClaw adapter token 无效"})


@router.get("/healthz")
def adapter_healthz():
    return {"status": "ok", "service": "aegis-openclaw-adapter", "mode": "local-dev-skeleton"}


@router.post("/chat")
def adapter_chat(payload: AdapterChatRequest, authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)

    message = (payload.message or "").strip() or "请帮我分析这些附件。"
    attachment_notes = [f"已接收附件：{item.name}（{item.type}）" for item in payload.attachments]
    suggestions = mock_suggestions(message[:120] or "移动端 AI 问答", message, "medium")

    reply_parts = [
        "结论：当前 OpenClaw Adapter 处于本地联调骨架模式。",
        f"问题理解：{message}",
    ]
    if attachment_notes:
        reply_parts.append("我已结合这些附件一起看：\n" + "\n".join(f"- {item}" for item in attachment_notes))
    reply_parts.append("建议下一步：\n" + "\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(suggestions[:5])))

    return {
        "ok": True,
        "mode": "openclaw",
        "conversation_id": payload.conversation_id or "adapter-chat",
        "summary": "当前已接入本地 OpenClaw Adapter 骨架，后续可替换为真实 OpenClaw 执行链路。",
        "reply": "\n\n".join(reply_parts),
        "severity": "medium",
        "suggestions": suggestions,
        "attachment_notes": attachment_notes,
        "elapsed_ms": 10,
    }


@router.post("/diagnose")
def adapter_diagnose(payload: AdapterDiagnoseRequest, authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    result = mock_diagnose(payload.title, payload.detail, payload.severity)
    return {
        "ok": True,
        "mode": "openclaw",
        "summary": "当前由本地 OpenClaw Adapter 骨架返回诊断结果。",
        "severity": result.get("severity", payload.severity),
        "suggestions": result.get("suggestions", []),
        "elapsed_ms": 10,
    }


@router.post("/log-analyze")
def adapter_log_analyze(payload: AdapterLogAnalyzeRequest, authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    result = offline_rule_analyze(payload.detail, payload.severity)
    return {
        "ok": True,
        "mode": "openclaw",
        "summary": result.get("summary", ""),
        "severity": result.get("severity", payload.severity),
        "matched_rules": result.get("matched_rules", []),
        "suggestions": result.get("suggestions", []),
        "excerpt": result.get("excerpt", ""),
        "elapsed_ms": 10,
    }
