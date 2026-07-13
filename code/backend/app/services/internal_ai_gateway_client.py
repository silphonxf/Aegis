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

    def _is_pi_gateway(self, config: Optional[Dict[str, Any]] = None) -> bool:
        provider = (config or {}).get("engine_type") or settings.INTERNAL_AI_GATEWAY_PROVIDER
        return str(provider).lower() in {"pi_gateway", "pi-gateway"}

    def _headers(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        provider = str((config or {}).get("engine_type") or settings.INTERNAL_AI_GATEWAY_PROVIDER)
        headers = {
            "Content-Type": "application/json",
            "X-Aegis-AI-Provider": provider,
        }
        api_key = str((config or {}).get("api_key") or settings.INTERNAL_AI_GATEWAY_API_KEY or "")
        if api_key:
            if self._is_pi_gateway(config):
                headers["x-api-key"] = api_key
            else:
                headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def post_json(self, path: str, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base_url = str((config or {}).get("base_url") or settings.INTERNAL_AI_GATEWAY_BASE_URL or "").rstrip("/")
        timeout = int((config or {}).get("timeout_seconds") or settings.INTERNAL_AI_GATEWAY_TIMEOUT_SECONDS)
        if not base_url:
            raise InternalAIGatewayClientError("internal_gateway 未配置 INTERNAL_AI_GATEWAY_BASE_URL")

        url = f"{base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(config), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
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
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self._is_pi_gateway(config):
            return self._pi_chat(message=message, conversation_id=conversation_id, attachments=attachments or [], history=history or [], summary=summary, config=config)

        response = self.post_json(
            (config or {}).get("chat_path") or settings.INTERNAL_AI_GATEWAY_CHAT_PATH,
            {
                "provider": (config or {}).get("engine_type") or settings.INTERNAL_AI_GATEWAY_PROVIDER,
                "model": (config or {}).get("model") or settings.INTERNAL_AI_GATEWAY_MODEL,
                "conversation_id": conversation_id,
                "message": message,
                "attachments": attachments or [],
                "history": history or [],
                "summary": summary,
                "task": "chat",
            },
            config,
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

    def diagnose(self, *, title: str, detail: str, severity: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._is_pi_gateway(config):
            prompt = (
                "你是 Aegis 的运维诊断助手。请只返回 JSON 对象，不要输出 markdown。"
                "字段必须包含 summary(string), severity(low|medium|high), suggestions(string数组)。\n\n"
                f"标题：{title}\n当前严重级别：{severity}\n详情：\n{detail}"
            )
            response = self._pi_messages(prompt, system="你负责输出可机器解析的运维诊断 JSON。", config=config)
            parsed = self._extract_object(response)
            return {
                "summary": str(parsed.get("summary") or ""),
                "severity": self._normalize_severity(parsed.get("severity"), severity),
                "suggestions": self._extract_string_list(parsed.get("suggestions")),
                "raw_response": response,
            }

        response = self.post_json(
            (config or {}).get("diagnose_path") or settings.INTERNAL_AI_GATEWAY_DIAGNOSE_PATH,
            {
                "provider": (config or {}).get("engine_type") or settings.INTERNAL_AI_GATEWAY_PROVIDER,
                "model": (config or {}).get("model") or settings.INTERNAL_AI_GATEWAY_MODEL,
                "title": title,
                "detail": detail,
                "severity": severity,
                "task": "diagnose",
            },
            config,
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
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self._is_pi_gateway(config):
            prompt = (
                "你是 Aegis 的故障日志分析助手。请只返回 JSON 对象，不要输出 markdown。"
                "字段必须包含 summary(string), severity(low|medium|high), matched_rules(array), "
                "suggestions(string数组), excerpt(string)。matched_rules 每项至少包含 code 与 severity。\n\n"
                f"标题：{title}\n来源类型：{source_type}\n来源引用：{source_ref or ''}\n当前严重级别：{severity}\n日志详情：\n{detail}"
            )
            response = self._pi_messages(prompt, system="你负责输出可机器解析的日志分析 JSON。", config=config)
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

        response = self.post_json(
            (config or {}).get("log_analyze_path") or settings.INTERNAL_AI_GATEWAY_LOG_ANALYZE_PATH,
            {
                "provider": (config or {}).get("engine_type") or settings.INTERNAL_AI_GATEWAY_PROVIDER,
                "model": (config or {}).get("model") or settings.INTERNAL_AI_GATEWAY_MODEL,
                "title": title,
                "detail": detail,
                "severity": severity,
                "source_type": source_type,
                "source_ref": source_ref,
                "task": "log_analyze",
            },
            config,
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

    def _pi_messages(self, message: str, system: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        messages: List[Dict[str, str]] = []
        for item in (history or [])[-12:]:
            role = item.get("role") or "user"
            content = str(item.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message.strip() or "请帮我分析当前问题。"})
        payload: Dict[str, Any] = {
            "model": (config or {}).get("model") or settings.INTERNAL_AI_GATEWAY_MODEL,
            "max_tokens": 1200,
            "stream": False,
            "messages": messages,
        }
        if system and system.strip():
            payload["system"] = system.strip()
        return self.post_json((config or {}).get("chat_path") or settings.INTERNAL_AI_GATEWAY_CHAT_PATH, payload, config)

    def _pi_chat(
        self,
        *,
        message: str,
        conversation_id: Optional[str],
        attachments: List[Dict[str, Any]],
        history: List[Dict[str, str]],
        summary: Optional[str],
        config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        text_parts: List[str] = []
        if summary and summary.strip():
            text_parts.append(f"历史摘要：\n{summary.strip()[:1200]}")
        if message and message.strip():
            text_parts.append(message.strip())
        if attachments:
            attachment_lines = []
            for item in attachments:
                name = str(item.get("name") or "未命名附件")
                kind = str(item.get("type") or "application/octet-stream")
                size = int(item.get("size") or 0)
                extracted = str(item.get("extracted_text") or "").strip()
                if extracted:
                    attachment_lines.append(f"- {name} ({kind}, {size} bytes)\n{extracted[:1500]}")
                else:
                    attachment_lines.append(f"- {name} ({kind}, {size} bytes)")
            text_parts.append("附件信息：\n" + "\n\n".join(attachment_lines))
        response = self._pi_messages(
            "\n\n".join(text_parts) or "请帮我分析这些内容。",
            system="你是 Aegis 运维助手，请用中文给出清晰、可执行的回复。",
            history=history,
            config=config,
        )
        reply = self._extract_text(response)
        return {
            "conversation_id": conversation_id or str(response.get("id") or "pi-gateway-chat"),
            "summary": "本次对话由 Pi Gateway 返回。",
            "reply": reply,
            "severity": "medium",
            "suggestions": [],
            "attachment_notes": [],
            "raw_response": response,
        }

    def _extract_text(self, response: Dict[str, Any]) -> str:
        if response.get("type") == "error":
            error = response.get("error") if isinstance(response.get("error"), dict) else {}
            raise InternalAIGatewayClientError(str(error.get("message") or "Pi Gateway 返回错误"))

        content = response.get("content")
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                for key in ("text", "content", "output_text"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        parts.append(value.strip())
                        break
            text = "\n\n".join(parts).strip()
            if text:
                return text

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
