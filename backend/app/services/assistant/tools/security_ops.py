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
    html = _build_ip_reputation_html(items, summary)
    return {
        "success": True,
        "summary": summary,
        "data": result,
        "cards": [
            {
                "type": "inspection_records",
                "title": "IP 恶意地址分析",
                "summary": summary,
                "html_report": html,
                "items": card_items,
            }
        ],
        "actions": [],
    }


def _escape_html(value: object) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def _build_ip_reputation_html(items: list[dict], summary: str) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{_escape_html(item.get('ip'))}</td>"
        f"<td>{_escape_html(item.get('risk_level'))}</td>"
        f"<td>{'是' if item.get('is_malicious') else '否'}</td>"
        f"<td>{_escape_html(item.get('severity') or '-')}</td>"
        f"<td>{_escape_html(item.get('decision') or '-')}</td>"
        f"<td>{_escape_html(item.get('summary') or '-')}</td>"
        "</tr>"
        for item in items
    ) or "<tr><td colspan=\"6\">暂无结果</td></tr>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IP 恶意地址分析报告</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f5f7fb;color:#162b3f}}main{{max-width:1080px;margin:0 auto;padding:24px}}section{{background:#fff;border:1px solid #dce6f0;border-radius:12px;padding:18px;margin:14px 0}}table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #edf2f7;text-align:left;padding:10px;vertical-align:top}}th{{background:#f8fbff}}</style></head>
<body><main><h1>IP 恶意地址分析报告</h1><p>{_escape_html(summary)}</p><section><table><thead><tr><th>IP</th><th>风险</th><th>恶意</th><th>严重级别</th><th>处置建议</th><th>说明</th></tr></thead><tbody>{rows}</tbody></table></section></main></body></html>"""



def register_security_ops_tools(registry) -> None:
    registry.register(ToolSpec(name='analyze_capture_content', description='抓取 URL 并分析抓包内容', handler=analyze_capture_content))
    registry.register(ToolSpec(name='analyze_system_error_logs', description='读取并分析系统错误日志', handler=analyze_system_error_logs))
    registry.register(ToolSpec(name='analyze_ip_reputation', description='分析 IP 恶意地址情报', handler=analyze_ip_reputation))
