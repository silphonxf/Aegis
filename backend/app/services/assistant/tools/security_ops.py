from __future__ import annotations

from ipaddress import ip_address
import re
from typing import Any, Dict, List, Optional

from app.api.toolbox import _fetch_url_capture, _normalize_capture_url, _read_selected_logs, _resolve_time_range
from app.schemas.offline_ai import OfflineAnalyzeRequest
from app.services.ai_provider import run_offline_analyze
from app.services.assistant.schemas import ToolSpec
from app.services.threatbook import ThreatbookError, batch_query_ip_reputation


def analyze_capture_content(url: Optional[str] = None, severity: str = 'medium', note: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    target_url = (url or '').strip()
    if not target_url:
        return {"success": False, "summary": "请先提供要抓取分析的 URL。", "data": {}, "cards": [], "actions": []}
    target_url = _normalize_capture_url(target_url)
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

    local_results = []
    public_items = []
    for raw in raw_items:
        candidate = raw.strip()
        try:
            parsed = ip_address(candidate)
        except ValueError:
            return {"success": False, "summary": f"{candidate} 不是合法的 IP 地址。", "data": {}, "cards": [], "actions": []}
        if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved or parsed.is_multicast:
            local_results.append(_build_non_public_ip_result(str(parsed), parsed))
        else:
            public_items.append(str(parsed))

    if not public_items:
        summary = _summarize_ip_user_result(local_results)
        html = _build_ip_reputation_html(local_results, summary)
        return {
            "success": True,
            "summary": summary,
            "data": {"items": local_results},
            "cards": [
                {
                    "type": "inspection_records",
                    "title": "IP 风险研判",
                    "summary": summary,
                    "html_report": html,
                    "items": [{"label": item.get("ip", "-"), "value": item.get("user_verdict", "-")} for item in local_results],
                }
            ],
            "actions": [],
        }

    try:
        result = batch_query_ip_reputation(public_items, lang='zh', realtime_verdict=True)
    except ThreatbookError as exc:
        return {"success": False, "summary": f"IP 恶意地址分析失败：{exc}", "data": {}, "cards": [], "actions": []}
    items = [_build_public_ip_user_result(item) for item in (result.get('items') or [])]
    all_items = local_results + items
    summary = _summarize_ip_user_result(all_items)
    card_items = [{"label": item.get('ip', '-'), "value": item.get('user_verdict', '-')} for item in all_items[:10]]
    html = _build_ip_reputation_html(all_items, summary)
    return {
        "success": True,
        "summary": summary,
        "data": {**result, "items": all_items},
        "cards": [
            {
                "type": "inspection_records",
                "title": "IP 风险研判",
                "summary": summary,
                "html_report": html,
                "items": card_items,
            }
        ],
        "actions": [],
    }


def _build_non_public_ip_result(ip: str, parsed) -> dict:
    if parsed.is_private:
        ip_type = "私有地址"
        suggestion = "先确认它在内网中对应哪台设备，再结合访问行为判断。"
    elif parsed.is_loopback:
        ip_type = "本机回环地址"
        suggestion = "它只代表本机访问，重点排查本机进程和日志。"
    elif parsed.is_link_local:
        ip_type = "链路本地地址"
        suggestion = "它通常只在本地链路内有效，先确认来源网卡和设备。"
    else:
        ip_type = "非公网地址"
        suggestion = "它不适合直接按公网威胁情报判断，建议结合本地日志继续排查。"
    return {
        "ip": ip,
        "risk_level": "internal",
        "is_malicious": False,
        "user_verdict": "不是公网恶意 IP",
        "user_summary": f"{ip} 属于{ip_type}，不能按公网恶意 IP 直接判定。",
        "suggestion": suggestion,
        "summary": f"{ip_type}，不适合直接做公网威胁情报判断。",
    }


def _build_public_ip_user_result(item: dict) -> dict:
    risk_level = item.get("risk_level") or "unknown"
    is_malicious = bool(item.get("is_malicious"))
    should_block = bool(item.get("should_block"))
    needs_confirmation = bool(item.get("needs_manual_confirmation"))
    if should_block:
        verdict = "高风险，建议拦截"
        suggestion = "建议加入封禁或阻断策略，并保留相关访问日志。"
    elif needs_confirmation:
        verdict = "可疑，需人工确认"
        suggestion = "建议先核对业务归属和访问行为，再决定是否封禁。"
    elif is_malicious or risk_level in {"high_risk", "medium_risk", "suspicious"}:
        verdict = "可疑，建议复核"
        suggestion = "建议查看访问频率、目标端口和命中日志后再处置。"
    else:
        verdict = "未发现明显恶意"
        suggestion = "暂不建议直接封禁，继续观察异常访问行为。"
    return {
        **item,
        "user_verdict": verdict,
        "user_summary": f"{item.get('ip', '-')}：{verdict}。",
        "suggestion": suggestion,
    }


def _summarize_ip_user_result(items: list[dict]) -> str:
    if not items:
        return "未得到有效 IP 研判结果。"
    if len(items) == 1:
        item = items[0]
        verdict = item.get("user_verdict")
        prefix = f"{item.get('ip')} {verdict}。" if verdict else ""
        return f"{prefix}{item.get('user_summary') or item.get('summary') or '已完成 IP 研判'} 建议：{item.get('suggestion') or '继续结合日志确认。'}"
    risky = [item for item in items if item.get("user_verdict") in {"高风险，建议拦截", "可疑，需人工确认", "可疑，建议复核"}]
    internal = [item for item in items if item.get("risk_level") == "internal"]
    if risky:
        return f"已研判 {len(items)} 个 IP，其中 {len(risky)} 个需要重点关注。"
    if internal and len(internal) == len(items):
        return f"已研判 {len(items)} 个 IP，均为非公网地址，不能直接按公网恶意 IP 判断。"
    return f"已研判 {len(items)} 个 IP，未发现明显恶意公网 IP。"


def _escape_html(value: object) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def _build_ip_reputation_html(items: list[dict], summary: str) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{_escape_html(item.get('ip'))}</td>"
        f"<td>{_escape_html(item.get('user_verdict') or '-')}</td>"
        f"<td>{_escape_html(item.get('suggestion') or '-')}</td>"
        f"<td>{_escape_html(item.get('summary') or '-')}</td>"
        "</tr>"
        for item in items
    ) or "<tr><td colspan=\"4\">暂无结果</td></tr>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IP 风险研判报告</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f5f7fb;color:#162b3f}}main{{max-width:1080px;margin:0 auto;padding:24px}}section{{background:#fff;border:1px solid #dce6f0;border-radius:12px;padding:18px;margin:14px 0}}table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #edf2f7;text-align:left;padding:10px;vertical-align:top}}th{{background:#f8fbff}}</style></head>
<body><main><h1>IP 风险研判报告</h1><p>{_escape_html(summary)}</p><section><table><thead><tr><th>IP</th><th>结论</th><th>建议</th><th>说明</th></tr></thead><tbody>{rows}</tbody></table></section></main></body></html>"""



def register_security_ops_tools(registry) -> None:
    registry.register(ToolSpec(name='analyze_capture_content', description='抓取 URL 并分析抓包内容', handler=analyze_capture_content))
    registry.register(ToolSpec(name='analyze_system_error_logs', description='读取并分析系统错误日志', handler=analyze_system_error_logs))
    registry.register(ToolSpec(name='analyze_ip_reputation', description='分析 IP 恶意地址情报', handler=analyze_ip_reputation))
