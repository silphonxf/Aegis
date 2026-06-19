from __future__ import annotations

from typing import Any, Dict

from app.schemas.offline_ai import OfflineAnalyzeRequest
from app.services.ai_provider import run_offline_analyze
from app.services.assistant.schemas import ToolSpec



def analyze_log_text(text: str = "", **_: Any) -> Dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned:
        return {"success": False, "summary": "未提供日志文本", "data": {}}

    payload = OfflineAnalyzeRequest(
        title="Assistant 日志分析",
        source_type="manual",
        severity="medium",
        detail=cleaned[:20000],
    )
    result = run_offline_analyze(payload)
    summary = result.get("summary") or "已完成日志分析。"
    suggestions = result.get("suggestions") or []
    matched_rules = result.get("matched_rules") or []
    excerpt = result.get("excerpt") or cleaned[:800]
    severity = result.get("severity") or "medium"
    mode = result.get("mode") or "unknown"

    cards = [
        {
            "type": "log_analysis",
            "title": "日志分析",
            "summary": summary,
            "items": [
                {"label": "严重级别", "value": severity},
                {"label": "分析模式", "value": mode},
                {"label": "命中规则", "value": "、".join(rule.get("code", "") for rule in matched_rules if rule.get("code")) or "未命中"},
            ],
        }
    ]
    if suggestions:
        cards.append(
            {
                "type": "log_suggestions",
                "title": "排查建议",
                "items": [{"label": f"建议{i + 1}", "value": item} for i, item in enumerate(suggestions[:5])],
            }
        )

    return {
        "success": True,
        "summary": summary,
        "cards": cards,
        "data": {
            "excerpt": excerpt,
            "suggestions": suggestions,
            "matched_rules": matched_rules,
            "severity": severity,
            "mode": mode,
        },
        "actions": [
            {"type": "followup_suggestion", "label": "继续分析这段日志", "payload": {"intent": "analyze_log_text"}},
        ],
    }


def register_ai_analysis_tools(registry) -> None:
    registry.register(ToolSpec(name="analyze_log_text", description="分析日志文本", handler=analyze_log_text, risk_level="medium"))
