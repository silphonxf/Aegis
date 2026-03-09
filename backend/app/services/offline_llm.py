import json
import re
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings


class OfflineLLMError(RuntimeError):
    pass


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore") if e.fp else str(e)
        raise OfflineLLMError(f"HTTP {e.code}: {detail[:300]}") from e
    except urllib.error.URLError as e:
        raise OfflineLLMError(f"连接离线模型失败: {e}") from e
    except json.JSONDecodeError as e:
        raise OfflineLLMError(f"离线模型返回非 JSON: {e}") from e


def _extract_json(text: str) -> dict[str, Any]:
    # 支持模型返回 markdown code block 或纯 JSON
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1)

    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        text = text[first : last + 1]

    return json.loads(text)


def diagnose_with_ollama(title: str, detail: str, severity: str) -> tuple[str, list[str], str]:
    prompt = f"""
你是企业运维故障分析助手。请仅返回 JSON（不要任何额外文本），格式：
{{
  "severity": "low|medium|high",
  "summary": "一句话问题摘要",
  "suggestions": ["建议1", "建议2", "建议3"]
}}

输入信息：
- 标题: {title}
- 原始严重级别: {severity}
- 日志/现象: {detail}

要求：
1) suggestions 2~5 条，按排障优先级排序。
2) 建议要可执行、简明，不要空话。
3) 如不确定，建议里明确写“先验证/先确认”。
""".strip()

    resp = _post_json(
        f"{settings.OFFLINE_AI_OLLAMA_BASE_URL.rstrip('/')}/api/generate",
        {
            "model": settings.OFFLINE_AI_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=settings.OFFLINE_AI_TIMEOUT_SECONDS,
    )
    text = resp.get("response", "")
    data = _extract_json(text)

    out_severity = str(data.get("severity") or severity).lower()
    if out_severity not in {"low", "medium", "high"}:
        out_severity = severity

    suggestions = [str(x).strip() for x in (data.get("suggestions") or []) if str(x).strip()]
    if not suggestions:
        raise OfflineLLMError("离线模型未返回有效 suggestions")

    summary = str(data.get("summary") or "已完成离线诊断").strip()
    return out_severity, suggestions[:5], summary


def offline_analyze_with_ollama(title: str, detail: str, severity: str) -> tuple[str, str, list[str], list[dict[str, str]]]:
    prompt = f"""
你是离线错误日志分析引擎。请仅返回 JSON：
{{
  "severity": "low|medium|high",
  "summary": "一句话结论",
  "suggestions": ["建议1", "建议2", "建议3"],
  "matched_rules": [{{"code":"RULE_CODE","severity":"low|medium|high"}}]
}}

输入：
- 标题: {title}
- 原始严重级别: {severity}
- 日志: {detail}

要求：
1) matched_rules 可为空数组，但 code 必须是大写下划线风格。
2) suggestions 2~6 条，优先给可落地排障步骤。
""".strip()

    resp = _post_json(
        f"{settings.OFFLINE_AI_OLLAMA_BASE_URL.rstrip('/')}/api/generate",
        {
            "model": settings.OFFLINE_AI_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=settings.OFFLINE_AI_TIMEOUT_SECONDS,
    )
    text = resp.get("response", "")
    data = _extract_json(text)

    out_severity = str(data.get("severity") or severity).lower()
    if out_severity not in {"low", "medium", "high"}:
        out_severity = severity

    summary = str(data.get("summary") or "离线分析完成").strip()
    suggestions = [str(x).strip() for x in (data.get("suggestions") or []) if str(x).strip()]
    if not suggestions:
        raise OfflineLLMError("离线模型未返回有效 suggestions")

    matched_rules_raw = data.get("matched_rules") or []

    matched_rules: list[dict[str, str]] = []
    for item in matched_rules_raw:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().upper().replace("-", "_")
        sev = str(item.get("severity") or out_severity).lower()
        if not code:
            continue
        if sev not in {"low", "medium", "high"}:
            sev = out_severity
        matched_rules.append({"code": code, "severity": sev})

    return out_severity, summary, suggestions[:6], matched_rules
