from __future__ import annotations

from ipaddress import ip_address
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from app.core.config import settings

THREATBOOK_URL = "https://api.threatbook.cn/v3/scene/ip_reputation"
DEFAULT_MALICIOUS_JUDGMENTS = {
    "Spam",
    "Zombie",
    "Scanner",
    "Exploit",
    "Botnet",
    "Brute Force",
}


class ThreatbookError(Exception):
    pass


def validate_ip(value: str) -> str:
    ip = value.strip()
    if not ip:
        raise ThreatbookError("IP 不能为空")
    try:
        return str(ip_address(ip))
    except ValueError as exc:
        raise ThreatbookError(f"非法 IP：{value}") from exc


def normalize_ip_list(raw_items: List[str]) -> List[str]:
    values: List[str] = []
    seen: Set[str] = set()
    for raw in raw_items:
        for part in str(raw).replace("\n", ",").replace("\t", ",").split(","):
            candidate = part.strip()
            if not candidate:
                continue
            ip = validate_ip(candidate)
            if ip not in seen:
                seen.add(ip)
                values.append(ip)
    return values


def fetch_ip_reputation(ips: List[str], lang: str = "zh", realtime_verdict: bool = True) -> Dict[str, Any]:
    if not settings.THREATBOOK_API_KEY:
        raise ThreatbookError("未配置微步 API Key")
    if not ips:
        raise ThreatbookError("没有可查询的 IP")
    if len(ips) > 100:
        raise ThreatbookError("单次最多查询 100 个 IP")

    payload = {
        "apikey": settings.THREATBOOK_API_KEY,
        "resource": ",".join(ips),
        "lang": lang,
        "realtime_verdict": str(bool(realtime_verdict)).lower(),
    }

    try:
        response = requests.post(THREATBOOK_URL, data=payload, timeout=settings.THREATBOOK_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ThreatbookError(f"请求微步失败：{exc}") from exc
    except ValueError as exc:
        raise ThreatbookError("微步返回了无法解析的 JSON") from exc

    if data.get("response_code") != 0:
        raise ThreatbookError(data.get("verbose_msg") or f"微步返回异常：{data.get('response_code')}")
    return data


def summarize_ip_record(ip: str, record: Dict[str, Any]) -> Dict[str, Any]:
    basic = record.get("basic") or {}
    location = basic.get("location") or {}
    judgments = [str(item) for item in (record.get("judgments") or [])]
    malicious_hits = [item for item in judgments if item in DEFAULT_MALICIOUS_JUDGMENTS]
    tags_classes = record.get("tags_classes") or []
    tag_names = []
    for item in tags_classes:
        tags = item.get("tags")
        if isinstance(tags, list):
            tag_names.extend([str(tag) for tag in tags if str(tag).strip()])
        elif tags:
            tag_names.append(str(tags))

    confidence = str(record.get("confidence_level") or "").lower()
    severity = str(record.get("severity") or "info").lower()
    asn = record.get("asn") or {}
    asn_rank = asn.get("rank")
    is_malicious = bool(record.get("is_malicious"))

    risk_score = 0
    if is_malicious:
        risk_score += 50
    risk_score += {"low": 5, "medium": 15, "high": 25}.get(confidence, 0)
    risk_score += {"info": 0, "low": 5, "medium": 15, "high": 25, "critical": 35}.get(severity, 0)
    if isinstance(asn_rank, int):
        risk_score += asn_rank * 4
    if malicious_hits:
        risk_score += min(len(malicious_hits) * 5, 15)

    if is_malicious and severity in {"critical", "high"}:
        risk_level = "high_risk"
    elif is_malicious and severity == "medium":
        risk_level = "medium_risk"
    elif is_malicious or confidence == "high" or (isinstance(asn_rank, int) and asn_rank >= 3):
        risk_level = "suspicious"
    else:
        risk_level = "safe"

    city = str(location.get("city") or "").strip()
    needs_manual_confirmation = city == "济南" and risk_level in {"high_risk", "medium_risk", "suspicious"}
    should_block = is_malicious and city != "济南"
    location_text = " / ".join(filter(None, [location.get("country"), location.get("province"), location.get("city")])) or "-"

    reasons: List[str] = []
    if is_malicious:
        reasons.append("微步判定为恶意 IP")
    if severity:
        reasons.append(f"严重级别：{severity}")
    if confidence:
        reasons.append(f"可信度：{confidence}")
    if malicious_hits:
        reasons.append(f"命中威胁类型：{', '.join(malicious_hits)}")
    if isinstance(asn_rank, int):
        reasons.append(f"ASN 风险值：{asn_rank}")

    decision = "confirm_then_block" if needs_manual_confirmation else ("block" if should_block else ("review" if risk_level in {"medium_risk", "suspicious"} else "allow"))

    if city == "济南" and risk_level in {"high_risk", "medium_risk", "suspicious"}:
        reasons.append("归属地为济南，高危时需二次确认后再封禁")
    elif should_block:
        reasons.append("is_malicious=true 且归属地非济南，满足自动封禁条件")

    return {
        "ip": ip,
        "is_malicious": is_malicious,
        "confidence_level": confidence or None,
        "severity": severity,
        "judgments": judgments,
        "malicious_judgments": malicious_hits,
        "tags": tag_names,
        "asn": {
            "number": asn.get("number"),
            "info": asn.get("info"),
            "rank": asn_rank,
        },
        "basic": {
            "carrier": basic.get("carrier"),
            "location": {
                "country": location.get("country"),
                "country_code": location.get("country_code"),
                "province": location.get("province"),
                "city": location.get("city"),
                "lng": location.get("lng"),
                "lat": location.get("lat"),
                "display": location_text,
            },
        },
        "scene": record.get("scene"),
        "update_time": record.get("update_time"),
        "permalink": record.get("permalink"),
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "should_block": should_block,
        "needs_manual_confirmation": needs_manual_confirmation,
        "decision": decision,
        "summary": "；".join(reasons) if reasons else "未命中明显威胁情报",
        "raw": record,
    }


def batch_query_ip_reputation(raw_items: List[str], lang: str = "zh", realtime_verdict: bool = True) -> Dict[str, Any]:
    ips = normalize_ip_list(raw_items)
    data = fetch_ip_reputation(ips, lang=lang, realtime_verdict=realtime_verdict)
    ip_map = data.get("data", {}).get("ips") or data.get("ips") or {}
    items = [summarize_ip_record(ip, ip_map.get(ip) or {}) for ip in ips]
    high_risk_count = sum(1 for item in items if item["risk_level"] == "high_risk")
    malicious_count = sum(1 for item in items if item["is_malicious"])
    return {
        "query": {
            "ips": ips,
            "count": len(ips),
            "lang": lang,
            "realtime_verdict": realtime_verdict,
        },
        "summary": {
            "total": len(items),
            "malicious": malicious_count,
            "high_risk": high_risk_count,
            "block_candidates": [item["ip"] for item in items if item["should_block"]],
        },
        "items": items,
        "response_code": data.get("response_code"),
        "verbose_msg": data.get("verbose_msg"),
    }
