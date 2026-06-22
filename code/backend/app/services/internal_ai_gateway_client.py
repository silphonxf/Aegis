import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.core.config import settings


class InternalAIGatewayClientError(RuntimeError):
    pass


class InternalAIGatewayClient:
    def is_configured(self) -> bool:
        return bool((settings.INTERNAL_AI_GATEWAY_BASE_URL or "").strip())

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Aegis-AI-Provider": settings.INTERNAL_AI_GATEWAY_PROVIDER,
        }
        if settings.INTERNAL_AI_GATEWAY_API_KEY:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_AI_GATEWAY_API_KEY}"
        return headers

    def post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        base_url = (settings.INTERNAL_AI_GATEWAY_BASE_URL or "").rstrip("/")
        if not base_url:
            raise InternalAIGatewayClientError("internal_gateway 未配置 INTERNAL_AI_GATEWAY_BASE_URL")

        url = f"{base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=settings.INTERNAL_AI_GATEWAY_TIMEOUT_SECONDS) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore") if e.fp else str(e)
            raise InternalAIGatewayClientError(f"internal_gateway HTTP {e.code}: {detail[:300]}") from e
        except urllib.error.URLError as e:
            raise InternalAIGatewayClientError(f"internal_gateway 连接失败: {e}") from e
        except json.JSONDecodeError as e:
            raise InternalAIGatewayClientError(f"internal_gateway 返回非 JSON: {e}") from e

    def chat(
        self,
        *,
        message: str,
        conversation_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        response = self.post_json(
            settings.INTERNAL_AI_GATEWAY_CHAT_PATH,
            {
                "provider": settings.INTERNAL_AI_GATEWAY_PROVIDER,
                "model": settings.INTERNAL_AI_GATEWAY_MODEL,
                "conversation_id": conversation_id,
                "message": message,
                "attachments": attachments or [],
                "history": history or [],
                "summary": summary,
                "task": "chat",
            },
        )
        reply = self._extract_text(response)
        return {
            "conversation_id": str(response.get("conversation_id") or conversation_id or "internal-gateway-chat"),
            "summary": str(response.get("summary") or "本次对话由内部 AI 网关返回。"),
            "reply": reply,
            "severity": str(response.get("severity") or "medium"),
            "suggestions": self._extract_string_list(response.get("suggestions")),
            "attachment_notes": self._extract_string_list(response.get("attachment_notes")),
            "raw_response": response,
        }

    def diagnose(self, *, title: str, detail: str, severity: str) -> Dict[str, Any]:
        response = self.post_json(
            settings.INTERNAL_AI_GATEWAY_DIAGNOSE_PATH,
            {
                "provider": settings.INTERNAL_AI_GATEWAY_PROVIDER,
                "model": settings.INTERNAL_AI_GATEWAY_MODEL,
                "title": title,
                "detail": detail,
                "severity": severity,
                "task": "diagnose",
            },
        )
        parsed = self._extract_object(response)
        return {
            "summary": str(parsed.get("summary") or ""),
            "severity": self._normalize_severity(parsed.get("severity"), severity),
            "suggestions": self._extract_string_list(parsed.get("suggestions")),
            "raw_response": response,
        }

    def log_analyze(
        self,
        *,
        title: str,
        detail: str,
        severity: str,
        source_type: str = "manual",
        source_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        response = self.post_json(
            settings.INTERNAL_AI_GATEWAY_LOG_ANALYZE_PATH,
            {
                "provider": settings.INTERNAL_AI_GATEWAY_PROVIDER,
                "model": settings.INTERNAL_AI_GATEWAY_MODEL,
                "title": title,
                "detail": detail,
                "severity": severity,
                "source_type": source_type,
                "source_ref": source_ref,
                "task": "log_analyze",
            },
        )
        parsed = self._extract_object(response)
        matched_rules = parsed.get("matched_rules") or []
        return {
            "summary": str(parsed.get("summary") or ""),
            "severity": self._normalize_severity(parsed.get("severity"), severity),
            "matched_rules": matched_rules if isinstance(matched_rules, list) else [],
            "suggestions": self._extract_string_list(parsed.get("suggestions")),
            "excerpt": str(parsed.get("excerpt") or detail[:2000]),
            "raw_response": response,
        }

    def _extract_text(self, response: Dict[str, Any]) -> str:
        for key in ("reply", "text", "output_text", "response", "content"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] if isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first, dict) else {}
            if isinstance(message, dict) and str(message.get("content") or "").strip():
                return str(message.get("content")).strip()

        output = response.get("output")
        if isinstance(output, list):
            parts: List[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                for part in item.get("content") or []:
                    if isinstance(part, dict) and part.get("text"):
                        parts.append(str(part.get("text")))
            text = "\n\n".join(part.strip() for part in parts if part.strip()).strip()
            if text:
                return text

        raise InternalAIGatewayClientError("internal_gateway 返回为空")

    def _extract_object(self, response: Dict[str, Any]) -> Dict[str, Any]:
        data = response.get("data")
        if isinstance(data, dict):
            return data

        if any(key in response for key in ("summary", "severity", "suggestions", "matched_rules")):
            return response

        text = self._extract_text(response)
        candidate = text.strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as e:
            raise InternalAIGatewayClientError(f"internal_gateway JSON 解析失败: {e}") from e
        if not isinstance(parsed, dict):
            raise InternalAIGatewayClientError("internal_gateway 未返回 JSON 对象")
        return parsed

    def _extract_string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _normalize_severity(self, value: Any, fallback: str) -> str:
        severity = str(value or fallback).lower()
        return severity if severity in {"low", "medium", "high"} else fallback


internal_ai_gateway_client = InternalAIGatewayClient()
