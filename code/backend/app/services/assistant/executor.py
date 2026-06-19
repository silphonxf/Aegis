from __future__ import annotations

import logging
from typing import Dict

from app.schemas.assistant import AssistantAction, AssistantToolCall

from .context_manager import context_manager
from .entity_resolver import entity_resolver
from .policy import policy
from .response_builder import build_response
from .router import AssistantRouter, extract_system_name
from .tool_registry import registry
from .tools import register_all_tools

register_all_tools(registry)
logger = logging.getLogger(__name__)


def _extract_url_from_message(message: str) -> str | None:
    import re
    from urllib.parse import urlparse

    text = (message or "").strip()
    if not text:
        return None

    patterns = [
        r'https?\s*:?//[^\s，。；;、,]+',
        r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d{2,5})?(?:/[^\s，。；;、,]*)?',
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            break
    if not match:
        return None

    candidate = match.group(0).strip('，。；;、,')
    candidate = re.sub(r'^(https?)\s*:?//', r'\1://', candidate, flags=re.I)
    if candidate.lower().startswith("http//"):
        candidate = "http://" + candidate[6:]
    elif candidate.lower().startswith("https//"):
        candidate = "https://" + candidate[7:]
    elif not re.match(r'^https?://', candidate, flags=re.I):
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    netloc = parsed.netloc
    if netloc and re.search(r'[\u4e00-\u9fff]', netloc):
        trimmed_netloc = re.split(r'[\u4e00-\u9fff]', netloc, maxsplit=1)[0]
        if "." in trimmed_netloc:
            candidate = f"{parsed.scheme}://{trimmed_netloc}"
    return candidate


class AssistantExecutor:
    def __init__(self) -> None:
        self.router = AssistantRouter()

    def _build_tool_arguments(self, tool: str | None, message: str, ctx: dict, attachments: list[dict], route_arguments: dict | None = None) -> dict:
        if not tool:
            return {}
        route_args = dict(route_arguments or {})
        system_aware_tools = {
            "list_accessible_systems",
            "run_system_selfcheck_report",
            "get_system_status_overview",
            "get_system_detail",
            "list_inspection_records",
            "list_selfcheck_records",
            "create_restart_approval",
            "analyze_log_text",
        }
        base = entity_resolver.resolve(message, ctx, route_args) if tool in system_aware_tools else route_args
        if tool == "list_accessible_systems":
            extracted_system_name = base.get("system_name") or extract_system_name(message)
            return {"system_name": extracted_system_name} if extracted_system_name else {}
        if tool == "run_system_selfcheck_report":
            args = {}
            system_name = base.get("system_name") or extract_system_name(message)
            if system_name:
                args["system_name"] = system_name
            elif base.get("system_id"):
                args["system_id"] = base["system_id"]
            if base.get("range_minutes"):
                args["range_minutes"] = base["range_minutes"]
            return args
        if tool in {"get_system_status_overview", "get_system_detail", "list_inspection_records", "list_selfcheck_records", "create_restart_approval"}:
            args = {}
            system_name = base.get("system_name") or extract_system_name(message)
            if system_name:
                args["system_name"] = system_name
            if base.get("system_id"):
                args["system_id"] = base["system_id"]
            return args
        if tool in {"get_abnormal_systems", "get_monitoring_overview", "collect_local_status_snapshot"}:
            return {}
        if tool in {"read_recent_error_logs", "analyze_system_error_logs"}:
            return {k: base[k] for k in ("source", "level", "quick_range") if base.get(k)}
        if tool == "list_tool_tasks":
            return {"status": base["status"]} if base.get("status") else {}
        if tool == "run_ping_check":
            args = {}
            import re
            host_match = re.search(r'((?:\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|localhost)', message)
            if base.get("host"):
                args["host"] = str(base["host"])
            if host_match:
                args.setdefault("host", host_match.group(1))
            return args
        if tool == "analyze_capture_content":
            args = {}
            url_candidate = str(base.get("url") or "").strip()
            url = _extract_url_from_message(url_candidate) if url_candidate else _extract_url_from_message(message)
            if url:
                args["url"] = url
            if base.get("severity"):
                args["severity"] = str(base["severity"])
            if base.get("note"):
                args["note"] = str(base["note"])
            return args
        if tool == "analyze_ip_reputation":
            import re
            explicit_ip = str(base.get("ip") or "").strip()
            ips = re.findall(r'(?:\d{1,3}\.){3}\d{1,3}', explicit_ip or message)
            return {"ip": ','.join(ips)} if ips else {}
        if tool == "run_port_check":
            args = {}
            import re
            host_match = re.search(r'((?:\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|localhost)', message)
            port_match = re.search(r'(?:端口|port)\s*[:：]?\s*(\d{2,5})', lower if 'lower' in locals() else message.lower())
            if base.get("host"):
                args["host"] = str(base["host"])
            if base.get("port"):
                try:
                    args["port"] = int(base["port"])
                except (TypeError, ValueError):
                    pass
            if host_match:
                args.setdefault("host", host_match.group(1))
            if port_match:
                args.setdefault("port", int(port_match.group(1)))
            return args
        if tool == "analyze_log_text":
            attachment_text = "\n\n".join(
                f"附件 {item.get('name') or '未命名'}：\n{(item.get('extracted_text') or '').strip()}"
                for item in attachments
                if isinstance(item, dict) and (item.get("extracted_text") or "").strip()
            ).strip()
            explicit_text = str(base.get("text") or "").strip()
            args = {"text": "\n\n".join(part for part in [explicit_text or message, attachment_text] if part).strip()}
            if base.get("system_name"):
                args["system_name"] = base["system_name"]
            if base.get("system_id"):
                args["system_id"] = base["system_id"]
            return args
        return {}

    def chat(self, conversation_id: str | None, message: str, attachments: list[dict] | None = None):
        conv_id, ctx = context_manager.ensure(conversation_id)
        history = list(ctx.get("messages") or [])
        route = self.router.route(message, history=history, attachments=attachments or [])
        route.arguments = self._build_tool_arguments(route.tool, message, ctx, attachments or [], route.arguments)
        logger.info("assistant_route_resolved: message=%s tool=%s intent=%s arguments=%s", message, route.tool, route.intent, route.arguments)
        ctx["messages"].append({"role": "user", "content": message})

        if not route.tool:
            reply = route.reply or "我暂时没理解你的意图。"
            route_actions = [AssistantAction(**item) for item in (route.actions or [])]
            actions = route_actions or [AssistantAction(type="assistant_hint", label="查看可用能力", payload={"intents": ["系统状态", "巡检", "自检", "日志分析", "重启审批"]})]
            ctx["messages"].append({"role": "assistant", "content": reply})
            context_manager.update(conv_id, ctx)
            return build_response(
                conv_id,
                reply,
                intent=route.intent,
                actions=actions,
                cards=route.cards or [],
                data=route.data or {},
                context=ctx,
            )

        spec = registry.get(route.tool)
        if not spec or not spec.handler:
            reply = f"工具 {route.tool} 暂不可用。"
            ctx["messages"].append({"role": "assistant", "content": reply})
            context_manager.update(conv_id, ctx)
            return build_response(conv_id, reply, intent=route.intent, context=ctx)

        if route.arguments.get("system_name"):
            ctx["last_system_name"] = route.arguments.get("system_name")

        if policy.requires_confirmation(spec):
            pending = policy.build_pending_action(spec, route.arguments)
            ctx["last_pending_action"] = pending
            reply = f"即将执行高风险动作：{spec.description}。请确认是否继续。"
            ctx["messages"].append({"role": "assistant", "content": reply})
            context_manager.update(conv_id, ctx)
            return build_response(
                conv_id,
                reply,
                intent=route.intent,
                tool_calls=[AssistantToolCall(tool=spec.name, arguments=route.arguments)],
                actions=[
                    AssistantAction(type="confirm_action", label="确认执行", payload={"action_id": pending["action_id"]}),
                    AssistantAction(type="cancel_action", label="取消执行", payload={"action_id": pending["action_id"]}),
                ],
                cards=[{"type": "pending_confirmation", "title": "待确认动作", "detail": pending}],
                data={"pending_action": pending},
                requires_confirmation=True,
                pending_action=pending,
                context=ctx,
            )

        result: Dict = spec.handler(**route.arguments)
        reply = result.get("summary") or route.reply or "操作已完成。"
        if not result.get("success") and not result.get("summary"):
            reply = "当前还不能完成这个查询。"
        ctx["last_tool"] = spec.name
        data = result.get("data") or {}
        if data.get("system_name"):
            ctx["last_system_name"] = data.get("system_name")
        elif route.arguments.get("system_name"):
            ctx["last_system_name"] = route.arguments.get("system_name")
        if data.get("system_id"):
            ctx["last_system_id"] = data.get("system_id")
        elif route.arguments.get("system_id"):
            ctx["last_system_id"] = route.arguments.get("system_id")
        ctx["messages"].append({"role": "assistant", "content": reply})
        context_manager.update(conv_id, ctx)
        tool_actions = [AssistantAction(**item) for item in (result.get("actions") or [])]
        fallback_actions = [AssistantAction(type="followup_suggestion", label="继续追问", payload={"intent": route.intent})]
        return build_response(
            conv_id,
            reply,
            intent=route.intent,
            tool_calls=[AssistantToolCall(tool=spec.name, arguments=route.arguments)],
            actions=tool_actions or fallback_actions,
            cards=result.get("cards") or [],
            data=data,
            context=ctx,
        )

    def confirm(self, conversation_id: str, action_id: str, confirmed: bool):
        conv_id, ctx = context_manager.ensure(conversation_id)
        pending = ctx.get("last_pending_action")
        if not pending or pending.get("action_id") != action_id:
            return build_response(conv_id, "未找到待确认动作。", intent="confirm_action", context=ctx)
        if not confirmed:
            ctx["last_pending_action"] = None
            context_manager.update(conv_id, ctx)
            return build_response(conv_id, "已取消执行。", intent="confirm_action", actions=[AssistantAction(type="assistant_hint", label="继续其他操作", payload={})], context=ctx)

        spec = registry.get(pending["tool"])
        if not spec or not spec.handler:
            return build_response(conv_id, "待确认工具不可用。", intent="confirm_action", context=ctx)

        result: Dict = spec.handler(**pending.get("arguments", {}))
        reply = result.get("summary") or "已完成确认执行。"
        ctx["last_pending_action"] = None
        ctx["last_tool"] = spec.name
        data = result.get("data") or {}
        if data.get("system_name"):
            ctx["last_system_name"] = data.get("system_name")
        elif pending.get("arguments", {}).get("system_name"):
            ctx["last_system_name"] = pending.get("arguments", {}).get("system_name")
        if data.get("system_id"):
            ctx["last_system_id"] = data.get("system_id")
        elif pending.get("arguments", {}).get("system_id"):
            ctx["last_system_id"] = pending.get("arguments", {}).get("system_id")
        ctx["messages"].append({"role": "assistant", "content": reply})
        context_manager.update(conv_id, ctx)
        return build_response(
            conv_id,
            reply,
            intent=spec.name,
            actions=result.get("actions") or [AssistantAction(type="assistant_hint", label="继续其他操作", payload={})],
            cards=result.get("cards") or [],
            data=data,
            context=ctx,
        )
