from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.api.toolbox import _fetch_url_capture, _read_selected_logs, _resolve_time_range
from app.schemas.offline_ai import OfflineAnalyzeRequest
from app.services.ai_provider import run_offline_analyze
from app.services.assistant.schemas import ToolSpec
from app.services.threatbook import ThreatbookError, batch_query_ip_reputation


def analyze_capture_content(url: Optional[str] = None, severity: str = 'medium', note: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    target_url = (url or '').strip()
    if not target_url:
        return {"success": False, "summary": "请先提供要抓取分析的 URL。", "data": {}, "cards": [], "actions": []}
    capture = _fetch_url_capture(target_url)
    payload = OfflineAnalyzeRequest(
        title='抓包结果分析',
        detail=capture.get('content', ''),
        severity=severity,
        source_type='url_fetch',
        source_ref=note or target_url,
    )
    result = run_offline_analyze(payload)
    summary = result.get('summary') or '已完成抓包分析。'
    suggestions = result.get('suggestions') or []
    matched_rules = result.get('matched_rules') or []
    return {
        "success": True,
        "summary": summary,
        "data": {
            "url": target_url,
            "capture": capture,
            "analysis": result,
        },
        "cards": [
            {
                "type": "log_analysis",
                "title": "抓包分析",
                "summary": summary,
                "items": [
                    {"label": "URL", "value": target_url},
                    {"label": "HTTP 状态", "value": str(capture.get('status_code', '-'))},
                    {"label": "严重级别", "value": str(result.get('severity') or severity)},
                    {"label": "命中规则", "value": '、'.join(rule.get('code', '') for rule in matched_rules if rule.get('code')) or '未命中'},
                ],
            }
        ] + ([{
            "type": "log_suggestions",
            "title": "排查建议",
            "items": [{"label": f"建议{i+1}", "value": item} for i, item in enumerate(suggestions[:5])],
        }] if suggestions else []),
        "actions": [],
    }



def analyze_system_error_logs(level: str = 'warning', quick_range: str = '1h', source: str = 'system', **_: Any) -> Dict[str, Any]:
    start_dt, end_dt, _ = _resolve_time_range(quick_range, None, None)
    content, source_detail = _read_selected_logs(source=source, file_name=None, level=level, start_dt=start_dt, end_dt=end_dt, lines=400)
    if not content:
        return {
            "success": True,
            "summary": "当前没有读取到符合条件的系统日志。",
            "data": {"content": '', "source": source, "level": level, "quick_range": quick_range},
            "cards": [{"type": "log_analysis", "title": "系统日志分析", "summary": "当前没有读取到符合条件的系统日志。", "items": [{"label": "来源", "value": source}, {"label": "级别", "value": level}, {"label": "范围", "value": quick_range}]}],
            "actions": [],
        }
    payload = OfflineAnalyzeRequest(
        title='系统日志分析',
        detail=content[:20000],
        severity='medium',
        source_type='system_log',
        source_ref=source_detail,
    )
    result = run_offline_analyze(payload)
    summary = result.get('summary') or '已完成系统日志分析。'
    suggestions = result.get('suggestions') or []
    matched_rules = result.get('matched_rules') or []
    return {
        "success": True,
        "summary": summary,
        "data": {"content": content, "source": source, "level": level, "quick_range": quick_range, "analysis": result},
        "cards": [
            {
                "type": "log_analysis",
                "title": "系统日志分析",
                "summary": summary,
                "items": [
                    {"label": "来源", "value": source},
                    {"label": "级别", "value": level},
                    {"label": "范围", "value": quick_range},
                    {"label": "命中规则", "value": '、'.join(rule.get('code', '') for rule in matched_rules if rule.get('code')) or '未命中'},
                ],
            }
        ] + ([{
            "type": "log_suggestions",
            "title": "排查建议",
            "items": [{"label": f"建议{i+1}", "value": item} for i, item in enumerate(suggestions[:5])],
        }] if suggestions else []),
        "actions": [],
    }



def analyze_ip_reputation(ip: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    text = (ip or '').strip()
    if not text:
        return {"success": False, "summary": "请先提供要分析的 IP 地址。", "data": {}, "cards": [], "actions": []}
    raw_items: List[str] = re.findall(r'(?:\d{1,3}\.){3}\d{1,3}', text)
    if not raw_items:
        raw_items = [text]
    try:
        result = batch_query_ip_reputation(raw_items, lang='zh', realtime_verdict=True)
    except ThreatbookError as exc:
        return {"success": False, "summary": f"IP 恶意地址分析失败：{exc}", "data": {}, "cards": [], "actions": []}
    items = result.get('items') or []
    summary = f"已完成 {result.get('summary', {}).get('total', 0)} 个 IP 的恶意地址分析，高风险 {result.get('summary', {}).get('high_risk', 0)} 个。"
    card_items = []
    for item in items[:10]:
        card_items.append({"label": item.get('ip', '-'), "value": item.get('risk_level', 'unknown')})
    return {
        "success": True,
        "summary": summary,
        "data": result,
        "cards": [
            {
                "type": "inspection_records",
                "title": "IP 恶意地址分析",
                "summary": summary,
                "items": card_items,
            }
        ],
        "actions": [],
    }



def register_security_ops_tools(registry) -> None:
    registry.register(ToolSpec(name='analyze_capture_content', description='抓取 URL 并分析抓包内容', handler=analyze_capture_content))
    registry.register(ToolSpec(name='analyze_system_error_logs', description='读取并分析系统错误日志', handler=analyze_system_error_logs))
    registry.register(ToolSpec(name='analyze_ip_reputation', description='分析 IP 恶意地址情报', handler=analyze_ip_reputation))
