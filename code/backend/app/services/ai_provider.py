import time
from typing import Any, Dict, Iterator, List, Optional

from app.core.config import settings
from app.schemas.ai import ChatRequest
from app.schemas.offline_ai import OfflineAnalyzeRequest
from app.services.ai_engine_config import get_runtime_ai_config
from app.services.internal_ai_gateway_client import InternalAIGatewayClientError, internal_ai_gateway_client
from app.services.offline_llm import OfflineLLMError, diagnose_with_ollama, offline_analyze_with_ollama
from app.services.openclaw_client import OpenClawClientError, openclaw_client


OFFLINE_RULES = [
    {
        "code": "DB_CONN_FAIL",
        "pattern": r"(connection refused|could not connect|db.*timeout|数据库连接失败)",
        "severity": "high",
        "suggestion": "检查数据库连通性、账号权限、连接池上限；确认数据库实例状态正常。",
    },
    {
        "code": "DISK_FULL",
        "pattern": r"(no space left on device|disk full|磁盘.*已满)",
        "severity": "high",
        "suggestion": "清理日志与临时文件，扩容磁盘；为关键目录设置容量告警阈值。",
    },
    {
        "code": "OOM_KILLED",
        "pattern": r"(out of memory|oom-killer|killed process)",
        "severity": "high",
        "suggestion": "排查内存泄漏，限制进程内存，必要时分批任务并降低并发。",
    },
    {
        "code": "PORT_CONFLICT",
        "pattern": r"(address already in use|端口.*被占用)",
        "severity": "medium",
        "suggestion": "定位端口占用进程并释放，或调整服务端口并更新配置。",
    },
    {
        "code": "AUTH_FAILED",
        "pattern": r"(unauthorized|forbidden|invalid token|鉴权失败|权限不足)",
        "severity": "medium",
        "suggestion": "核对凭证有效期、签名密钥和角色权限映射，检查网关转发头。",
    },
    {
        "code": "SERVICE_TIMEOUT",
        "pattern": r"(timeout|timed out|read timeout|请求超时)",
        "severity": "medium",
        "suggestion": "检查下游RT、网络抖动与重试策略，避免无上限重试放大故障。",
    },
]


def _severity_rank(level: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(level, 1)


def mock_suggestions(title: str, detail: str, severity: str) -> List[str]:
    text = detail.lower()
    suggestions = []
    if "cpu" in text or "load" in text:
        suggestions.append("先检查最近15分钟CPU突增进程（top/ps），确认是否发布或批处理引发。")
    if "内存" in detail or "memory" in text:
        suggestions.append("检查内存泄漏与缓存命中率，必要时分时重启高占用服务。")
    if "连接" in detail or "timeout" in text:
        suggestions.append("优先排查网络连通、连接池上限、下游依赖RT抖动。")
    if not suggestions:
        suggestions = [
            "先定位影响范围（单实例/全局），再按CPU、内存、磁盘、网络四象限逐项排查。",
            "保留现场日志与关键指标快照，避免重启后丢失证据。",
        ]
    return suggestions


def mock_diagnose(title: str, detail: str, severity: str) -> Dict[str, Any]:
    return {
        "mode": "rule_fallback",
        "severity": severity,
        "summary": "离线模型未启用，已使用规则建议。",
        "suggestions": mock_suggestions(title, detail, severity),
        "fallback_reason": "offline_ai_disabled_or_provider_mismatch",
    }


def offline_rule_analyze(detail: str, fallback_severity: str) -> Dict[str, Any]:
    import re

    matched = []
    suggestions = []
    summary_items = []
    final_severity = fallback_severity

    for rule in OFFLINE_RULES:
        if re.search(rule["pattern"], detail, flags=re.I):
            matched.append({"code": rule["code"], "severity": rule["severity"]})
            suggestions.append(rule["suggestion"])
            summary_items.append(rule["code"])
            if _severity_rank(rule["severity"]) > _severity_rank(final_severity):
                final_severity = rule["severity"]

    if not matched:
        suggestions = [
            "未命中已知规则，请先按时间线定位首个报错，再关联上下游依赖日志进行排查。",
            "建议补充业务日志关键字段（trace_id/system_id/error_code）提升自动分析命中率。",
        ]
        summary = "未命中规则，建议人工复核。"
    else:
        summary = f"命中规则: {', '.join(summary_items)}"

    excerpt = "\n".join([ln for ln in detail.splitlines() if ln.strip()][:60])
    return {
        "mode": "rule_fallback",
        "severity": final_severity,
        "summary": summary,
        "matched_rules": matched,
        "suggestions": list(dict.fromkeys(suggestions)),
        "excerpt": excerpt,
        "fallback_reason": "offline_ai_disabled_or_provider_mismatch",
    }


def _call_provider(handler, fallback_reason: Optional[str], mode: str) -> Dict[str, Any]:
    started = time.perf_counter()
    data = handler()
    data.setdefault("elapsed_ms", int((time.perf_counter() - started) * 1000))
    data.setdefault("fallback_reason", fallback_reason)
    data.setdefault("mode", mode)
    return data


def run_diagnose(title: str, detail: str, severity: str) -> Dict[str, Any]:
    runtime_config = get_runtime_ai_config()
    provider = runtime_config.get("engine_type", settings.AI_PROVIDER).lower()
    started = time.perf_counter()

    try:
        if provider == "openclaw":
            return _call_provider(
                lambda: openclaw_client.diagnose(title=title, detail=detail, severity=severity, config=runtime_config),
                None,
                "openclaw",
            )

        if provider in {"internal_gateway", "pi_gateway"}:
            return _call_provider(
                lambda: internal_ai_gateway_client.diagnose(title=title, detail=detail, severity=severity, config=runtime_config),
                None,
                provider,
            )

        if provider in {"ollama", "offline"} and settings.OFFLINE_AI_ENABLED and settings.OFFLINE_AI_PROVIDER.lower() == "ollama":
            out_severity, suggestions, summary = diagnose_with_ollama(title, detail, severity)
            return {
                "mode": "offline_ollama",
                "severity": out_severity,
                "summary": summary,
                "suggestions": suggestions,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "fallback_reason": None,
            }
    except (OfflineLLMError, OpenClawClientError, InternalAIGatewayClientError) as e:
        fallback = mock_diagnose(title, detail, severity)
        fallback["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        fallback["fallback_reason"] = str(e)[:200]
        return fallback

    fallback = mock_diagnose(title, detail, severity)
    fallback["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    return fallback


def run_chat(
    payload: ChatRequest,
    history: Optional[List[Dict[str, str]]] = None,
    summary: Optional[str] = None,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    runtime_config = runtime_config or get_runtime_ai_config()
    provider = runtime_config.get("engine_type", settings.AI_PROVIDER).lower()
    started = time.perf_counter()

    if provider == "openclaw":
        try:
            return _call_provider(
                lambda: openclaw_client.chat(
                    message=payload.message,
                    conversation_id=payload.conversation_id,
                    attachments=[item.dict() for item in payload.attachments],
                    history=history or [],
                    summary=None,
                    config=runtime_config,
                ),
                None,
                "openclaw",
            )
        except OpenClawClientError as e:
            fallback_reason = str(e)[:200]
        else:
            fallback_reason = None
    elif provider in {"internal_gateway", "pi_gateway"}:
        try:
            return _call_provider(
                lambda: internal_ai_gateway_client.chat(
                    message=payload.message,
                    conversation_id=payload.conversation_id,
                    attachments=[item.dict() for item in payload.attachments],
                    history=history or [],
                    summary=summary,
                    config=runtime_config,
                ),
                None,
                provider,
            )
        except InternalAIGatewayClientError as e:
            fallback_reason = str(e)[:200]
    else:
        fallback_reason = None

    message = (payload.message or "").strip() or "请帮我分析这些附件。"
    attachment_notes = [f"已收到附件：{item.name}（{item.type}）" for item in payload.attachments]
    suggestions = mock_suggestions(message[:120] or "移动端 AI 问答", message, "medium")
    reply_parts = [
        "结论：当前仍使用本地 fallback 规则回复。",
        f"问题理解：{message}",
    ]
    if attachment_notes:
        reply_parts.append("我已结合这些附件一起看：\n" + "\n".join(f"- {item}" for item in attachment_notes))
    reply_parts.append("建议下一步：\n" + "\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(suggestions[:5])))
    return {
        "conversation_id": payload.conversation_id or "local-chat",
        "mode": "rule_fallback",
        "summary": "本次对话使用本地 fallback 规则回复。",
        "reply": "\n\n".join(reply_parts),
        "severity": "medium",
        "suggestions": suggestions,
        "attachment_notes": attachment_notes,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "fallback_reason": fallback_reason or "openclaw_not_enabled",
    }


def stream_chat(
    payload: ChatRequest,
    history: Optional[List[Dict[str, str]]] = None,
    summary: Optional[str] = None,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> Iterator[Dict[str, Any]]:
    """Stream chat deltas when supported and always finish with a result event."""
    config = runtime_config or get_runtime_ai_config()
    provider = str(config.get("engine_type") or settings.AI_PROVIDER).lower()
    if provider in {"internal_gateway", "pi_gateway"} and internal_ai_gateway_client._is_pi_gateway(config):
        started = time.perf_counter()
        text_parts: List[str] = []
        try:
            for text in internal_ai_gateway_client.stream_pi_messages(
                payload.message,
                system="你是 Aegis 运维助手，请用中文给出清晰、可执行的回复。",
                history=history or [],
                config=config,
            ):
                text_parts.append(text)
                yield {"type": "delta", "text": text}
            reply = "".join(text_parts).strip()
            if not reply:
                raise InternalAIGatewayClientError("Pi Gateway 流式返回为空")
            yield {
                "type": "done",
                "data": {
                    "conversation_id": payload.conversation_id or "pi-gateway-chat",
                    "mode": provider,
                    "summary": "本次对话由 Pi Gateway 流式返回。",
                    "reply": reply,
                    "severity": "medium",
                    "suggestions": [],
                    "attachment_notes": [],
                    "elapsed_ms": int((time.perf_counter() - started) * 1000),
                    "fallback_reason": None,
                },
            }
            return
        except InternalAIGatewayClientError:
            if text_parts:
                raise

    result = run_chat(payload, history=history, summary=summary, runtime_config=config)
    reply = str(result.get("reply") or result.get("summary") or "")
    if reply:
        yield {"type": "delta", "text": reply}
    yield {"type": "done", "data": result}


def stream_diagnose(title: str, detail: str, severity: str) -> Iterator[Dict[str, Any]]:
    """Stream diagnosis text; the done event contains the normalized diagnosis."""
    config = get_runtime_ai_config()
    provider = str(config.get("engine_type") or settings.AI_PROVIDER).lower()
    if provider in {"internal_gateway", "pi_gateway"} and internal_ai_gateway_client._is_pi_gateway(config):
        prompt = (
            "你是 Aegis 的运维诊断助手。请用中文输出诊断结论和可执行建议。\n\n"
            f"标题：{title}\n当前严重级别：{severity}\n详情：\n{detail}"
        )
        started = time.perf_counter()
        parts: List[str] = []
        try:
            for text in internal_ai_gateway_client.stream_pi_messages(
                prompt,
                system="你负责运维故障诊断，先给结论，再给分点建议。",
                config=config,
            ):
                parts.append(text)
                yield {"type": "delta", "text": text}
            summary = "".join(parts).strip()
            if not summary:
                raise InternalAIGatewayClientError("Pi Gateway 流式返回为空")
            result = {
                "mode": provider,
                "severity": severity,
                "summary": summary,
                "suggestions": [],
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "fallback_reason": None,
            }
            yield {"type": "done", "data": result}
            return
        except InternalAIGatewayClientError:
            if parts:
                raise

    result = run_diagnose(title, detail, severity)
    text = str(result.get("summary") or "")
    if text:
        yield {"type": "delta", "text": text}
    yield {"type": "done", "data": result}


def run_offline_analyze(payload: OfflineAnalyzeRequest) -> Dict[str, Any]:
    runtime_config = get_runtime_ai_config()
    provider = runtime_config.get("engine_type", settings.AI_PROVIDER).lower()
    started = time.perf_counter()

    try:
        if provider == "openclaw":
            return _call_provider(
                lambda: openclaw_client.log_analyze(
                    title=payload.title,
                    detail=payload.detail,
                    severity=payload.severity,
                    source_type=payload.source_type,
                    source_ref=payload.source_ref,
                    config=runtime_config,
                ),
                None,
                "openclaw",
            )

        if provider in {"internal_gateway", "pi_gateway"}:
            return _call_provider(
                lambda: internal_ai_gateway_client.log_analyze(
                    title=payload.title,
                    detail=payload.detail,
                    severity=payload.severity,
                    source_type=payload.source_type,
                    source_ref=payload.source_ref,
                    config=runtime_config,
                ),
                None,
                provider,
            )

        if provider in {"ollama", "offline"} and settings.OFFLINE_AI_ENABLED and settings.OFFLINE_AI_PROVIDER.lower() == "ollama":
            severity, summary, suggestions, matched_rules = offline_analyze_with_ollama(
                payload.title, payload.detail, payload.severity
            )
            excerpt = "\n".join([ln for ln in payload.detail.splitlines() if ln.strip()][:80])
            return {
                "mode": "offline_ollama",
                "severity": severity,
                "summary": summary,
                "matched_rules": matched_rules,
                "suggestions": suggestions,
                "excerpt": excerpt,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "fallback_reason": None,
            }
    except (OfflineLLMError, OpenClawClientError, InternalAIGatewayClientError) as e:
        fallback = offline_rule_analyze(payload.detail, payload.severity)
        fallback["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        fallback["fallback_reason"] = str(e)[:200]
        return fallback

    fallback = offline_rule_analyze(payload.detail, payload.severity)
    fallback["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    return fallback
