from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from app.core.config import settings
from app.schemas.ai import ChatAttachment, ChatRequest
from app.services.ai_provider import run_chat

from .fallback_router import AssistantFallbackRouter
from .schemas import RouteResult


_SYSTEM_NAME_RE = re.compile(r"((?:示例|演示|测试|生产|业务|平台|监控|运维|核心|支付|订单|用户|门户|调度|告警|数据|资产|巡检|自检|办公|本机)?[\u4e00-\u9fa5A-Za-z0-9_-]{1,24}系统)")
_STATUS_KEYWORDS = ["系统状态", "运行状态", "状态怎么样"]
_SYSTEM_LIST_KEYWORDS = ["有哪些系统", "有哪几个系统", "系统列表", "系统清单", "接入了哪些系统", "已接入系统"]
_OVERVIEW_KEYWORDS = ["监控总览", "总体情况", "整体状态", "总览"]
_ABNORMAL_KEYWORDS = ["异常系统", "系统异常"]
_DETAIL_KEYWORDS = ["系统详情", "详情", "详细信息", "详细情况"]
_INSPECTION_KEYWORDS = ["巡检", "巡检记录", "最近巡检"]
_SELFCHECK_KEYWORDS = ["自检", "自检记录", "最近自检"]
_RUN_SELFCHECK_KEYWORDS = ["智能自检", "进行一次自检", "执行自检", "自检报告", "生成自检"]
_LOG_KEYWORDS = ["日志", "报错", "错误", "异常堆栈", "报异常", "分析这段"]
_READ_LOG_KEYWORDS = ["最近错误日志", "读取日志", "看看日志", "最近日志"]
_SYSTEM_LOG_ANALYZE_KEYWORDS = ["系统日志分析", "分析系统日志", "分析错误日志", "分析最近日志"]
_CAPTURE_ANALYZE_KEYWORDS = ["抓包分析", "分析抓包", "抓取这个url", "抓这个url", "分析这个url", "接口抓包"]
_IP_REPUTATION_KEYWORDS = ["ip恶意地址分析", "恶意ip分析", "恶意ip", "ip信誉分析", "ip情报", "微步分析", "威胁情报ip", "ip威胁情报", "分析ip", "分析这个ip"]
_PING_KEYWORDS = ["ping", "连通性", "是否可达"]
_PORT_KEYWORDS = ["端口", "port"]
_TASK_KEYWORDS = ["工具任务", "任务列表", "最近任务"]
_LOCAL_COLLECT_KEYWORDS = ["采集本机状态", "采集状态", "本机状态"]
_RESTART_KEYWORDS = ["重启"]
_APPROVAL_KEYWORDS = ["审批", "发起", "申请"]


def _extract_system_name(text: str) -> Optional[str]:
    raw = text or ""
    match = _SYSTEM_NAME_RE.search(raw)
    if not match:
        return None
    candidate = match.group(1)
    if any(phrase in candidate for phrase in ["有哪几个系统", "有哪些系统", "接入了哪些系统", "已接入系统", "系统列表", "系统清单"]):
        return None
    return candidate


extract_system_name = _extract_system_name


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


class AssistantRouter:
    def __init__(self) -> None:
        self.fallback_router = AssistantFallbackRouter()

    def route(self, message: str, history: Optional[list[dict]] = None, attachments: Optional[list[dict]] = None) -> RouteResult:
        text = (message or "").strip()
        ai_result = self._route_via_ai(text, history=history or [], attachments=attachments or [])
        if ai_result:
            return ai_result
        return self._route_by_rules(text, attachments=attachments or [])

    def _route_by_rules(self, text: str, attachments: Optional[list[dict]] = None) -> RouteResult:
        system_name = _extract_system_name(text)
        base_args = {"system_name": system_name} if system_name else {}
        has_text_attachment = any((item.get("extracted_text") or "").strip() for item in attachments or [] if isinstance(item, dict))
        wants_attachment_analysis = has_text_attachment and (
            not text
            or any(keyword in text for keyword in ["附件", "文件", "分析", "判断", "看看", "排查", "原因"])
        )

        if _contains_any(text, _SYSTEM_LIST_KEYWORDS):
            return RouteResult(intent="query_system_list", tool="list_accessible_systems", arguments=base_args)
        if _contains_any(text, _OVERVIEW_KEYWORDS):
            return RouteResult(intent="query_monitoring_overview", tool="get_monitoring_overview", arguments={})
        if _contains_any(text, _DETAIL_KEYWORDS):
            return RouteResult(intent="query_system_detail", tool="get_system_detail", arguments=base_args)
        if _contains_any(text, _ABNORMAL_KEYWORDS):
            return RouteResult(intent="query_abnormal_systems", tool="get_abnormal_systems", arguments={})
        if _contains_any(text, _STATUS_KEYWORDS):
            return RouteResult(intent="query_system_status", tool="get_system_status_overview", arguments=base_args)
        if _contains_any(text, _INSPECTION_KEYWORDS):
            return RouteResult(intent="query_inspection_records", tool="list_inspection_records", arguments=base_args)
        if _contains_any(text, _RUN_SELFCHECK_KEYWORDS):
            return RouteResult(intent="run_system_selfcheck", tool="run_system_selfcheck_report", arguments=base_args)
        if _contains_any(text, _SELFCHECK_KEYWORDS):
            return RouteResult(intent="query_selfcheck_records", tool="list_selfcheck_records", arguments=base_args)
        if _contains_any(text, _READ_LOG_KEYWORDS):
            return RouteResult(intent="read_recent_error_logs", tool="read_recent_error_logs", arguments={})
        if _contains_any(text, _SYSTEM_LOG_ANALYZE_KEYWORDS):
            return RouteResult(intent="analyze_system_error_logs", tool="analyze_system_error_logs", arguments={})
        if _contains_any(text.lower(), _CAPTURE_ANALYZE_KEYWORDS):
            return RouteResult(intent="analyze_capture_content", tool="analyze_capture_content", arguments={})
        if wants_attachment_analysis:
            return RouteResult(intent="analyze_log_text", tool="analyze_log_text", arguments={})
        lowered = text.lower()
        has_ip_literal = bool(re.search(r'(?:\d{1,3}\.){3}\d{1,3}', text))
        if _contains_any(lowered, _IP_REPUTATION_KEYWORDS) or (has_ip_literal and any(keyword in lowered for keyword in ['恶意ip', 'ip', '威胁情报', '信誉'])):
            return RouteResult(intent="analyze_ip_reputation", tool="analyze_ip_reputation", arguments={})
        if _contains_any(text, _LOG_KEYWORDS):
            return RouteResult(intent="analyze_log_text", tool="analyze_log_text", arguments={"text": text, **base_args})
        if _contains_any(text.lower(), _PING_KEYWORDS):
            return RouteResult(intent="run_ping_check", tool="run_ping_check", arguments={})
        if _contains_any(text.lower(), _PORT_KEYWORDS):
            return RouteResult(intent="run_port_check", tool="run_port_check", arguments={})
        if _contains_any(text, _TASK_KEYWORDS):
            return RouteResult(intent="list_tool_tasks", tool="list_tool_tasks", arguments={})
        if _contains_any(text, _LOCAL_COLLECT_KEYWORDS):
            return RouteResult(intent="collect_local_status_snapshot", tool="collect_local_status_snapshot", arguments={})
        if _contains_any(text, _RESTART_KEYWORDS) and _contains_any(text, _APPROVAL_KEYWORDS):
            return RouteResult(intent="create_restart_approval", tool="create_restart_approval", arguments=base_args)

        return self.fallback_router.route(text)

    def _route_via_ai(self, text: str, history: list[dict], attachments: list[dict]) -> Optional[RouteResult]:
        if settings.AI_PROVIDER.lower() != 'openclaw' or not (settings.OPENCLAW_BASE_URL or '').strip():
            return None
        if not text and not attachments:
            return None

        prompt = self._build_route_prompt(text)
        try:
            result = run_chat(
                ChatRequest(
                    conversation_id=None,
                    message=prompt,
                    attachments=[ChatAttachment(**item) for item in attachments if isinstance(item, dict)],
                ),
                history=history[-8:],
                summary=None,
            )
            reply = (result.get('reply') or '').strip()
            parsed = self._extract_route_json(reply)
            if not parsed:
                return None
            return self._normalize_ai_route(parsed, original_message=text)
        except Exception:
            return None

    def _build_route_prompt(self, text: str) -> str:
        return (
            '你是 Aegis 移动端助手的意图路由器。请根据用户输入判断：是否应该直接自然回复，还是调用某个特定功能工具。'
            '只返回 JSON，不要输出任何额外说明。JSON 格式必须为：'
            '{"mode":"reply|tool","intent":"...","reply":"...","tool":"..."}。'
            '可用 tool 只有：list_accessible_systems,get_system_status_overview,get_system_detail,get_abnormal_systems,list_inspection_records,list_selfcheck_records,run_system_selfcheck_report,analyze_ip_reputation,analyze_capture_content,analyze_system_error_logs,analyze_log_text,create_restart_approval。'
            '规则：1) 普通寒暄/闲聊/追问优先 mode=reply，reply 要自然，不能模板化；'
            '2) 用户明确在查系统列表、状态、详情、巡检、自检、IP恶意研判、抓包分析、日志分析、重启审批时，用 mode=tool；'
            '3) 对于“我现在有哪几个系统/接入了哪些系统”这类问题，优先使用 list_accessible_systems；'
            '4) 不要臆造系统名、记录、状态结果，也不要返回 arguments；参数由后端自行决定。'
            '5) 没有对应能力时应选择 mode=reply 并明确说明当前未接入该能力。\n\n'
            f'用户输入：{text}'
        )

    def _extract_route_json(self, reply: str) -> Optional[Dict[str, Any]]:
        candidate = (reply or '').strip()
        if not candidate:
            return None
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find('{')
            end = candidate.rfind('}')
            if start >= 0 and end > start:
                try:
                    return json.loads(candidate[start:end + 1])
                except json.JSONDecodeError:
                    return None
        return None

    def _normalize_ai_route(self, payload: Dict[str, Any], original_message: str) -> Optional[RouteResult]:
        mode = str(payload.get('mode') or '').strip().lower()
        intent = str(payload.get('intent') or 'general_chat').strip() or 'general_chat'
        if mode == 'tool':
            tool = str(payload.get('tool') or '').strip()
            if not tool:
                return None
            return RouteResult(intent=intent, tool=tool, arguments={})

        reply = str(payload.get('reply') or '').strip()
        if reply:
            return RouteResult(intent=intent, reply=reply)
        return None
