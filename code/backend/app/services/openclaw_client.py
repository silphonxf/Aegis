import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.core.config import settings


class OpenClawClientError(RuntimeError):
    pass


class OpenClawClient:
    def __init__(self) -> None:
        self.base_url = (settings.OPENCLAW_BASE_URL or "").rstrip("/")
        self.api_key = settings.OPENCLAW_API_KEY or ""
        self.timeout = settings.OPENCLAW_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _headers(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = (config or {}).get("api_key") or self.api_key
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def post_json(self, path: str, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base_url = ((config or {}).get("base_url") or self.base_url).rstrip("/")
        timeout = int((config or {}).get("timeout_seconds") or self.timeout)
        if not base_url:
            raise OpenClawClientError("OpenClaw provider 未配置 OPENCLAW_BASE_URL")

        url = f"{base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(config), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore") if e.fp else str(e)
            raise OpenClawClientError(f"OpenClaw HTTP {e.code}: {detail[:300]}") from e
        except urllib.error.URLError as e:
            raise OpenClawClientError(f"OpenClaw 连接失败: {e}") from e
        except json.JSONDecodeError as e:
            raise OpenClawClientError(f"OpenClaw 返回非 JSON: {e}") from e

    def chat(self, *, message: str, conversation_id: Optional[str] = None, attachments: Optional[List[Dict[str, Any]]] = None, history: Optional[List[Dict[str, str]]] = None, summary: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        model = (config or {}).get("model") or settings.OPENCLAW_MODEL
        path = (config or {}).get("chat_path") or settings.OPENCLAW_RESPONSES_PATH
        response = self.post_json(
            path,
            {
                "model": model,
                "input": self._build_chat_input(message=message, attachments=attachments or [], history=history or [], summary=summary),
            },
            config,
        )
        text = self._extract_response_text(response)
        return {
            "conversation_id": conversation_id or response.get("id") or "openclaw-chat",
            "summary": "本次对话由 OpenClaw Gateway 返回。",
            "reply": text,
            "raw_response": response,
        }

    def diagnose(self, *, title: str, detail: str, severity: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        model = (config or {}).get("model") or settings.OPENCLAW_MODEL
        path = (config or {}).get("diagnose_path") or (config or {}).get("chat_path") or settings.OPENCLAW_RESPONSES_PATH
        prompt = (
            "你是 Aegis 的运维诊断助手。请基于给定故障信息，返回 JSON，字段必须包含："
            "summary(string), severity(low|medium|high), suggestions(string数组)。"
            "不要输出 markdown，不要输出额外解释。\n\n"
            f"标题：{title}\n"
            f"当前严重级别：{severity}\n"
            f"详情：\n{detail}"
        )
        response = self.post_json(
            path,
            {
                "model": model,
                "input": prompt,
            },
            config,
        )
        text = self._extract_response_text(response)
        parsed = self._extract_json_object(text)
        return {
            "summary": str(parsed.get("summary") or ""),
            "severity": str(parsed.get("severity") or severity),
            "suggestions": [str(item) for item in (parsed.get("suggestions") or []) if str(item).strip()],
            "raw_response": response,
        }

    def log_analyze(self, *, title: str, detail: str, severity: str, source_type: str = "manual", source_ref: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        model = (config or {}).get("model") or settings.OPENCLAW_MODEL
        path = (config or {}).get("log_analyze_path") or (config or {}).get("chat_path") or settings.OPENCLAW_RESPONSES_PATH
        prompt = (
            "你是 Aegis 的离线日志分析助手。请基于输入日志返回 JSON，字段必须包含："
            "summary(string), severity(low|medium|high), matched_rules(array), suggestions(string数组), excerpt(string)。"
            "matched_rules 每项至少包含 code 与 severity。"
            "不要输出 markdown，不要输出额外解释。\n\n"
            f"标题：{title}\n"
            f"来源类型：{source_type}\n"
            f"来源引用：{source_ref or ''}\n"
            f"当前严重级别：{severity}\n"
            f"日志详情：\n{detail}"
        )
        response = self.post_json(
            path,
            {
                "model": model,
                "input": prompt,
            },
            config,
        )
        text = self._extract_response_text(response)
        parsed = self._extract_json_object(text)
        matched_rules = parsed.get("matched_rules") or []
        return {
            "summary": str(parsed.get("summary") or ""),
            "severity": str(parsed.get("severity") or severity),
            "matched_rules": matched_rules if isinstance(matched_rules, list) else [],
            "suggestions": [str(item) for item in (parsed.get("suggestions") or []) if str(item).strip()],
            "excerpt": str(parsed.get("excerpt") or detail[:2000]),
            "raw_response": response,
        }

    def _build_chat_input(self, *, message: str, attachments: List[Dict[str, Any]], history: List[Dict[str, str]], summary: Optional[str]) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        if summary and summary.strip():
            messages.append({
                "type": "message",
                "role": "system",
                "content": [{"type": "input_text", "text": f"以下是当前会话的历史摘要，请在回答时延续这些上下文：\n{summary.strip()[:1200]}"}],
            })
        for item in history[-12:]:
            role = item.get("role") or "user"
            text = str(item.get("content") or "").strip()
            if not text:
                continue
            messages.append({
                "type": "message",
                "role": role,
                "content": [{"type": "input_text", "text": text}],
            })

        content: List[Dict[str, Any]] = []
        text_parts = []
        if message.strip():
            text_parts.append(message.strip())
        if attachments:
            attachment_lines = []
            for item in attachments:
                name = str(item.get("name") or "未命名附件")
                kind = str(item.get("type") or "application/octet-stream")
                size = int(item.get("size") or 0)
                attachment_lines.append(f"- {name} ({kind}, {size} bytes)")
            text_parts.append("附件信息：\n" + "\n".join(attachment_lines))
        content.append({"type": "input_text", "text": "\n\n".join(text_parts) or "请帮我分析这些内容。"})
        messages.append({"type": "message", "role": "user", "content": content})
        return messages

    def _extract_response_text(self, response: Dict[str, Any]) -> str:
        outputs = response.get("output") or []
        text_parts: List[str] = []
        for item in outputs:
            if item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if part.get("type") == "output_text" and part.get("text"):
                    text_parts.append(str(part.get("text")))
        text = "\n\n".join(part.strip() for part in text_parts if str(part).strip()).strip()
        if not text:
            raise OpenClawClientError("OpenClaw 返回为空")
        return text

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        candidate = text.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(candidate[start : end + 1])
                except json.JSONDecodeError as e:
                    raise OpenClawClientError(f"OpenClaw JSON 解析失败: {e}") from e
            raise OpenClawClientError("OpenClaw 未返回有效 JSON")


openclaw_client = OpenClawClient()
