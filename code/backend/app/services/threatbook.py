from __future__ import annotations

from ipaddress import ip_address
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests

from app.core.config import settings

THREATBOOK_IP_QUERY_URL = "https://api.threatbook.cn/v3/ip/query"
THREATBOOK_DOMAIN_QUERY_URL = "https://api.threatbook.cn/v3/domain/query"
DEFAULT_MALICIOUS_JUDGMENTS = {
    "Spam",
    "Zombie",
    "Scanner",
    "Exploit",
    "Botnet",
    "Brute Force",
}
SAFE_JUDGMENTS = {"Whitelist", "CDN", "DNS", "Gateway", "ICP", "Search Engine", "Cloud Provider"}


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


def validate_domain(value: str) -> str:
    candidate = value.strip().lower().rstrip(".")
    if "://" in candidate:
        candidate = urlparse(candidate).hostname or ""
    candidate = candidate.split("/")[0].split(":")[0].rstrip(".")
    try:
        ascii_domain = candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ThreatbookError(f"非法域名：{value}") from exc
    if len(ascii_domain) > 253 or "." not in ascii_domain:
        raise ThreatbookError(f"非法域名：{value}")
    labels = ascii_domain.split(".")
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
        raise ThreatbookError(f"非法域名：{value}")
    return ascii_domain


def normalize_indicators(raw_items: List[str]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for raw in raw_items:
        for part in re.split(r"[\s,，;；]+", str(raw)):
            candidate = part.strip()
            if not candidate:
                continue
            try:
                value = str(ip_address(candidate))
                kind = "ip"
            except ValueError:
                value = validate_domain(candidate)
                kind = "domain"
            key = (kind, value)
            if key not in seen:
                seen.add(key)
                items.append({"type": kind, "value": value})
    if not items:
        raise ThreatbookError("没有可查询的 IP 或域名")
    if len(items) > 100:
        raise ThreatbookError("单次最多查询 100 个 IP 或域名")
    return items


def _fetch_resource(url: str, resource: str, lang: str) -> Dict[str, Any]:
    if not settings.THREATBOOK_API_KEY:
        raise ThreatbookError("未配置微步 API Key")
    try:
        response = requests.get(
            url,
            params={"apikey": settings.THREATBOOK_API_KEY, "resource": resource, "lang": lang},
            timeout=settings.THREATBOOK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ThreatbookError(f"请求微步失败：{exc}") from exc
    except ValueError as exc:
        raise ThreatbookError("微步返回了无法解析的 JSON") from exc
    if data.get("response_code") != 0:
        raise ThreatbookError(data.get("verbose_msg") or f"微步返回异常：{data.get('response_code')}")
    return data


def fetch_ip_reputation(ips: List[str], lang: str = "zh", realtime_verdict: bool = True) -> Dict[str, Any]:
    if not settings.THREATBOOK_API_KEY:
        raise ThreatbookError("未配置微步 API Key")
    if not ips:
        raise ThreatbookError("没有可查询的 IP")
    if len(ips) > 100:
        raise ThreatbookError("单次最多查询 100 个 IP")

    if len(ips) != 1:
        raise ThreatbookError("IP 分析接口每次仅支持查询一个 IP")
    return _fetch_resource(THREATBOOK_IP_QUERY_URL, ips[0], lang)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是", "恶意"}
    return False


def _extract_ip_records(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = data.get("data")
    if isinstance(payload, dict):
        nested_ips = payload.get("ips")
        if isinstance(nested_ips, dict):
            return nested_ips
        return payload

    top_level_ips = data.get("ips")
    if isinstance(top_level_ips, dict):
        return top_level_ips
    return {}


def summarize_ip_record(ip: str, record: Dict[str, Any]) -> Dict[str, Any]:
    basic = record.get("basic") or {}
    location = basic.get("location") or {}
    judgments = [str(item) for item in (record.get("judgments") or [])]
    intel_types = _extract_intel_types(record)
    malicious_hits = list(dict.fromkeys([item for item in judgments + intel_types if item not in SAFE_JUDGMENTS]))
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
    threatbook_malicious = _as_bool(record.get("is_malicious"))
    is_malicious = threatbook_malicious or bool(malicious_hits)

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
    if threatbook_malicious:
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
        reasons.append("命中恶意情报且归属地非济南，满足自动封禁条件")

    return {
        "resource": ip,
        "resource_type": "ip",
        "ip": ip,
        "ip_type": record.get("scene") or basic.get("carrier") or "未知",
        "country": location.get("country") or "未知",
        "malicious_types": malicious_hits,
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


def _extract_intel_types(record: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    intelligences = record.get("intelligences") or {}
    if isinstance(intelligences, dict):
        for entries in intelligences.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and not _as_bool(entry.get("expired")):
                    values.extend(str(item) for item in (entry.get("intel_types") or []) if str(item).strip())
    return list(dict.fromkeys(values))


def summarize_domain_record(domain: str, record: Dict[str, Any]) -> Dict[str, Any]:
    judgments = [str(item) for item in (record.get("judgments") or [])]
    intel_types = _extract_intel_types(record)
    malicious_types = list(dict.fromkeys([item for item in judgments + intel_types if item not in SAFE_JUDGMENTS]))
    samples = record.get("samples") or []
    sample_malicious = any(str(item.get("threat_level") or "").lower() == "malicious" for item in samples if isinstance(item, dict))
    is_malicious = bool(malicious_types) or sample_malicious
    cur_ips = record.get("cur_ips") or []
    countries = list(dict.fromkeys(
        str((item.get("location") or {}).get("country"))
        for item in cur_ips if isinstance(item, dict) and (item.get("location") or {}).get("country")
    ))
    categories: List[str] = []
    for item in record.get("categories") or []:
        if not isinstance(item, dict):
            continue
        categories.extend(str(value) for value in (item.get("first_cats") or []) if str(value).strip())
        second = item.get("second_cats")
        if second:
            categories.append(str(second))
    risk_level = "high_risk" if is_malicious else "safe"
    return {
        "resource": domain,
        "resource_type": "domain",
        "domain": domain,
        "domain_type": "、".join(dict.fromkeys(categories)) or "未知",
        "country": "、".join(countries) or "未知",
        "malicious_types": malicious_types,
        "judgments": judgments,
        "is_malicious": is_malicious,
        "risk_level": risk_level,
        "should_block": False,
        "needs_manual_confirmation": False,
        "decision": "review" if is_malicious else "allow",
        "resolved_ips": [item.get("ip") for item in cur_ips if isinstance(item, dict) and item.get("ip")],
        "whois": record.get("cur_whois") or {},
        "permalink": record.get("permalink"),
        "summary": f"恶意类型：{', '.join(malicious_types)}" if malicious_types else "未命中明显恶意域名情报",
        "raw": record,
    }


def batch_query_indicators(raw_items: List[str], lang: str = "zh") -> Dict[str, Any]:
    indicators = normalize_indicators(raw_items)
    items: List[Dict[str, Any]] = []
    for indicator in indicators:
        value = indicator["value"]
        if indicator["type"] == "ip":
            data = _fetch_resource(THREATBOOK_IP_QUERY_URL, value, lang)
            records = _extract_ip_records(data)
            items.append(summarize_ip_record(value, records.get(value) or {}))
        else:
            data = _fetch_resource(THREATBOOK_DOMAIN_QUERY_URL, value, lang)
            records = _extract_ip_records(data)
            items.append(summarize_domain_record(value, records.get(value) or {}))
    malicious = sum(1 for item in items if item["is_malicious"])
    return {
        "query": {"indicators": indicators, "count": len(indicators), "lang": lang},
        "summary": {
            "total": len(items),
            "ip_count": sum(1 for item in items if item["resource_type"] == "ip"),
            "domain_count": sum(1 for item in items if item["resource_type"] == "domain"),
            "malicious": malicious,
            "high_risk": sum(1 for item in items if item["risk_level"] == "high_risk"),
            "block_candidates": [item["ip"] for item in items if item.get("should_block")],
        },
        "items": items,
        "response_code": 0,
        "verbose_msg": "OK",
    }


def batch_query_ip_reputation(raw_items: List[str], lang: str = "zh", realtime_verdict: bool = True) -> Dict[str, Any]:
    ips = normalize_ip_list(raw_items)
    items: List[Dict[str, Any]] = []
    for ip in ips:
        data = fetch_ip_reputation([ip], lang=lang, realtime_verdict=realtime_verdict)
        records = _extract_ip_records(data)
        items.append(summarize_ip_record(ip, records.get(ip) or {}))
    return {
        "query": {"ips": ips, "count": len(ips), "lang": lang, "realtime_verdict": realtime_verdict},
        "summary": {
            "total": len(items),
            "ip_count": len(items),
            "domain_count": 0,
            "malicious": sum(1 for item in items if item["is_malicious"]),
            "high_risk": sum(1 for item in items if item["risk_level"] == "high_risk"),
            "block_candidates": [item["ip"] for item in items if item["should_block"]],
        },
        "items": items,
        "response_code": 0,
        "verbose_msg": "OK",
    }
