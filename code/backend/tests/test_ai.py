def test_ai_diagnose_and_history(client, admin_headers):
    diagnose = client.post(
        "/api/v1/ai/diagnose",
        headers=admin_headers,
        json={"title": "CPU高负载", "detail": "cpu load and timeout", "severity": "medium"},
    )
    assert diagnose.status_code == 200, diagnose.text
    body = diagnose.json()
    assert body["id"] > 0
    assert body["severity"] in {"low", "medium", "high"}
    assert isinstance(body["suggestions"], list)

    history = client.get("/api/v1/ai/diagnoses?page=1&size=10", headers=admin_headers)
    assert history.status_code == 200, history.text
    assert any(item["id"] == body["id"] for item in history.json()["items"])


def test_ai_offline_analyze_and_detail(client, admin_headers):
    analyze = client.post(
        "/api/v1/ai/offline/analyze",
        headers=admin_headers,
        json={
            "title": "数据库连接失败",
            "source_type": "manual",
            "source_ref": "pytest",
            "severity": "medium",
            "detail": "connection refused\ndb timeout\n数据库连接失败",
        },
    )
    assert analyze.status_code == 200, analyze.text
    body = analyze.json()
    assert body["task_id"] > 0
    assert isinstance(body["matched_rules"], list)

    detail = client.get(f"/api/v1/ai/offline/tasks/{body['task_id']}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["task"]["id"] == body["task_id"]


def test_internal_gateway_routes_chat_to_pi_agent(monkeypatch):
    import json
    import urllib.request

    from app.schemas.ai import ChatRequest
    from app.services import ai_provider

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "conversation_id": "gw-chat-1",
                    "reply": "pi-agent reply",
                    "summary": "gateway summary",
                    "suggestions": ["检查服务状态"],
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(ai_provider.settings, "AI_PROVIDER", "internal_gateway")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_BASE_URL", "https://gateway.local")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_API_KEY", "test-token")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_PROVIDER", "pi-agent")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_MODEL", "pi-agent-ops")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = ai_provider.run_chat(ChatRequest(message="分析 CPU 告警", conversation_id="conv-1"))

    assert result["mode"] == "internal_gateway"
    assert result["conversation_id"] == "gw-chat-1"
    assert result["reply"] == "pi-agent reply"
    assert captured["url"] == "https://gateway.local/v1/chat"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["headers"]["X-aegis-ai-provider"] == "pi-agent"
    assert captured["payload"]["provider"] == "pi-agent"
    assert captured["payload"]["model"] == "pi-agent-ops"
    assert captured["payload"]["task"] == "chat"
    assert captured["payload"]["message"] == "分析 CPU 告警"


def test_internal_gateway_routes_diagnose_and_log_analyze(monkeypatch):
    import json
    import urllib.request

    from app.schemas.offline_ai import OfflineAnalyzeRequest
    from app.services import ai_provider

    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(req, timeout):
        body = json.loads(req.data.decode("utf-8"))
        calls.append({"url": req.full_url, "payload": body})
        if body["task"] == "diagnose":
            return FakeResponse({"summary": "诊断完成", "severity": "high", "suggestions": ["先看日志"]})
        return FakeResponse(
            {
                "summary": "日志分析完成",
                "severity": "medium",
                "matched_rules": [{"code": "TIMEOUT", "severity": "medium"}],
                "suggestions": ["检查下游"],
                "excerpt": "timeout",
            }
        )

    monkeypatch.setattr(ai_provider.settings, "AI_PROVIDER", "internal_gateway")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_BASE_URL", "https://gateway.local")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_PROVIDER", "pi-agent")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_MODEL", "pi-agent-ops")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    diagnose = ai_provider.run_diagnose("故障", "timeout", "medium")
    log_result = ai_provider.run_offline_analyze(
        OfflineAnalyzeRequest(title="日志", detail="timeout", severity="low")
    )

    assert diagnose["mode"] == "internal_gateway"
    assert diagnose["severity"] == "high"
    assert diagnose["suggestions"] == ["先看日志"]
    assert log_result["mode"] == "internal_gateway"
    assert log_result["matched_rules"] == [{"code": "TIMEOUT", "severity": "medium"}]
    assert calls[0]["url"] == "https://gateway.local/v1/diagnose"
    assert calls[1]["url"] == "https://gateway.local/v1/log-analyze"
    assert calls[0]["payload"]["provider"] == "pi-agent"
    assert calls[1]["payload"]["provider"] == "pi-agent"


def test_internal_gateway_falls_back_when_unconfigured(monkeypatch):
    from app.schemas.ai import ChatRequest
    from app.services import ai_provider

    monkeypatch.setattr(ai_provider.settings, "AI_PROVIDER", "internal_gateway")
    monkeypatch.setattr(ai_provider.settings, "INTERNAL_AI_GATEWAY_BASE_URL", "")

    result = ai_provider.run_chat(ChatRequest(message="hello"))

    assert result["mode"] == "rule_fallback"
    assert "INTERNAL_AI_GATEWAY_BASE_URL" in result["fallback_reason"]


def test_assistant_chat_requires_login(client, admin_headers):
    anonymous = client.post(
        "/api/v1/assistant/chat",
        json={"message": "有哪些系统"},
    )
    assert anonymous.status_code == 401

    authed = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={"message": "有哪些系统"},
    )
    assert authed.status_code == 200, authed.text
    assert authed.json()["reply"]


def test_assistant_capture_tool_encodes_non_ascii_url(monkeypatch):
    from app.services.assistant.tools import security_ops

    captured = {}

    def fake_fetch(url):
        captured["url"] = url
        return {"content": "HTTP_STATUS: 200", "status_code": 200, "elapsed_ms": 1}

    def fake_analyze(payload):
        return {"summary": "已完成抓包分析。", "suggestions": [], "matched_rules": [], "severity": payload.severity}

    monkeypatch.setattr(security_ops, "_fetch_url_capture", fake_fetch)
    monkeypatch.setattr(security_ops, "run_offline_analyze", fake_analyze)

    result = security_ops.analyze_capture_content(url="https://example.com/接口/登录?备注=失败")

    assert result["success"] is True
    assert captured["url"] == "https://example.com/%E6%8E%A5%E5%8F%A3/%E7%99%BB%E5%BD%95?%E5%A4%87%E6%B3%A8=%E5%A4%B1%E8%B4%A5"
    captured["url"].encode("ascii")


def test_assistant_capture_ai_payload_is_compact(monkeypatch):
    from app.services.assistant.tools import security_ops

    seen = {}
    long_body = "x" * 5000

    def fake_fetch(url):
        return {
            "content": "\n".join(
                [
                    "URL: https://example.com/",
                    "HTTP_STATUS: 200",
                    "ELAPSED_MS: 12",
                    "RESPONSE_HEADERS:",
                    "Server: test",
                    "",
                    "RESPONSE_BODY_EXCERPT:",
                    long_body,
                ]
            ),
            "status_code": 200,
            "elapsed_ms": 12,
        }

    def fake_analyze(payload):
        seen["detail"] = payload.detail
        return {"summary": "已完成抓包分析。", "suggestions": [], "matched_rules": [], "severity": payload.severity}

    monkeypatch.setattr(security_ops, "_fetch_url_capture", fake_fetch)
    monkeypatch.setattr(security_ops, "run_offline_analyze", fake_analyze)

    result = security_ops.analyze_capture_content(url="https://example.com")

    assert result["success"] is True
    assert result["data"]["capture"]["content"].endswith(long_body)
    assert len(seen["detail"]) < 1600
    assert "RESPONSE_BODY_SHORT_EXCERPT" in seen["detail"]


def test_assistant_capture_url_extraction_trims_chinese_suffix():
    from app.services.assistant.executor import _extract_url_from_message

    assert _extract_url_from_message("帮我抓包分析一下http://baidu.com这个地址") == "http://baidu.com"
    assert _extract_url_from_message("抓包一下http//baidu.com") == "http://baidu.com"
    assert _extract_url_from_message("帮我分析 baidu.com 这个地址") == "https://baidu.com"


def test_assistant_tool_arguments_use_ai_extracted_arguments():
    from app.services.assistant.executor import AssistantExecutor

    executor = AssistantExecutor()

    capture_args = executor._build_tool_arguments(
        "analyze_capture_content",
        "抓包一下这个地址",
        {},
        [],
        {"url": "http//baidu.com", "note": "用户要求抓包"},
    )
    assert capture_args["url"] == "http://baidu.com"
    assert capture_args["note"] == "用户要求抓包"

    ping_args = executor._build_tool_arguments(
        "run_ping_check",
        "测一下连通性",
        {},
        [],
        {"host": "baidu.com"},
    )
    assert ping_args == {"host": "baidu.com"}

    port_args = executor._build_tool_arguments(
        "run_port_check",
        "测一下端口",
        {},
        [],
        {"host": "baidu.com", "port": "443"},
    )
    assert port_args == {"host": "baidu.com", "port": 443}


def test_assistant_router_prefers_rules_for_slow_tool_intents(monkeypatch):
    from app.services.assistant import router as router_module
    from app.services.assistant.router import AssistantRouter

    monkeypatch.setattr(router_module.settings, "AI_PROVIDER", "openclaw")
    monkeypatch.setattr(router_module.settings, "OPENCLAW_BASE_URL", "http://127.0.0.1:18789")

    def fail_ai_route(*args, **kwargs):
        raise AssertionError("explicit tool intents should not wait for AI route")

    monkeypatch.setattr(router_module, "run_chat", fail_ai_route)

    router = AssistantRouter()
    selfcheck = router.route("请对AI自检系统进行一次智能自检")
    assert selfcheck.tool == "run_system_selfcheck_report"

    uploaded_log = router.route(
        "请分析附件里的报错原因",
        attachments=[{"name": "backend-error.log", "extracted_text": "ERROR upstream timeout"}],
    )
    assert uploaded_log.tool == "analyze_log_text"


def test_external_assistant_chat_uses_admin_generated_apikey(client, admin_headers):
    missing = client.post(
        "/api/v1/assistant/external/chat",
        json={"message": "有哪些系统"},
    )
    assert missing.status_code == 422

    created = client.post(
        "/api/v1/admin/ai-external-keys",
        headers=admin_headers,
        json={"name": "pytest外部系统", "remark": "回归测试"},
    )
    assert created.status_code == 200, created.text
    key_body = created.json()
    assert key_body["apikey"].startswith("aegis_ai_")
    assert key_body["key_prefix"]

    listed = client.get("/api/v1/admin/ai-external-keys", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == key_body["id"] for item in listed.json()["items"])
    assert "apikey" not in listed.json()["items"][0]

    rejected = client.post(
        "/api/v1/assistant/external/chat",
        json={"apikey": "aegis_ai_invalid_but_long_enough", "message": "有哪些系统"},
    )
    assert rejected.status_code == 401

    authed = client.post(
        "/api/v1/assistant/external/chat",
        json={"apikey": key_body["apikey"], "message": "有哪些系统"},
    )
    assert authed.status_code == 200, authed.text
    assert authed.json()["reply"]

    disabled = client.patch(
        f"/api/v1/admin/ai-external-keys/{key_body['id']}/active?is_active=false",
        headers=admin_headers,
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["is_active"] is False

    rejected_after_disable = client.post(
        "/api/v1/assistant/external/chat",
        json={"apikey": key_body["apikey"], "message": "有哪些系统"},
    )
    assert rejected_after_disable.status_code == 401


def test_assistant_can_route_system_selfcheck(client, admin_headers):
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-AI-SC-001",
            "name": "AI自检系统",
            "host_address": "127.0.0.1",
            "env": "prod",
            "selfcheck_skill": "检查系统 CPU、内存、硬盘和告警信息，输出简短结论。",
        },
    )
    assert created.status_code == 200, created.text
    system_id = created.json()["id"]

    snapshot = client.post(
        f"/api/v1/systems/{system_id}/status/snapshot",
        headers=admin_headers,
        json={"host_online": "normal", "port_ok": "normal", "cpu_usage": 30, "mem_usage": 40, "disk_usage": 50},
    )
    assert snapshot.status_code == 200, snapshot.text

    resp = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={"message": "请对AI自检系统进行一次智能自检"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tool_calls"][0]["tool"] == "run_system_selfcheck_report"
    assert body["cards"][0]["html_report"].startswith("<!doctype html>")


def test_assistant_ip_reputation_private_ip_is_user_friendly(client, admin_headers):
    resp = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={"message": "10.11.123.4 是恶意 IP 吗"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tool_calls"][0]["tool"] == "analyze_ip_reputation"
    assert "不是公网恶意 IP" in body["reply"]
    assert "is_private" not in body["reply"]
    assert "bogon" not in body["reply"].lower()
    assert "is_global" not in body["reply"]


def test_assistant_ip_reputation_malicious_ip_is_explicit(monkeypatch):
    from app.services.assistant.tools import security_ops

    def fake_batch_query_ip_reputation(public_items, lang="zh", realtime_verdict=True):
        assert public_items == ["74.48.130.196"]
        return {
            "summary": {"total": 1, "malicious": 1, "high_risk": 0, "block_candidates": ["74.48.130.196"]},
            "items": [
                {
                    "ip": "74.48.130.196",
                    "is_malicious": True,
                    "risk_level": "medium_risk",
                    "should_block": True,
                    "needs_manual_confirmation": False,
                    "decision": "block",
                    "summary": "微步判定为恶意 IP；严重级别：中；可信度：高；ASN 风险值：4；命中恶意情报且归属地非济南，满足自动封禁条件",
                }
            ],
        }

    monkeypatch.setattr(security_ops, "batch_query_ip_reputation", fake_batch_query_ip_reputation)

    result = security_ops.analyze_ip_reputation(ip="74.48.130.196")

    assert result["success"] is True
    assert result["summary"].startswith("74.48.130.196：恶意 IP，高风险，建议拦截。")
    assert "恶意 IP，高风险，建议拦截" in result["summary"]
    assert "微步判定为恶意 IP" in result["summary"]
    assert "可疑，建议复核" not in result["summary"]
    assert result["data"]["items"][0]["user_verdict"] == "恶意 IP，高风险，建议拦截"


def test_assistant_can_analyze_uploaded_file_content(client, admin_headers):
    import base64

    created = client.post(
        "/api/v1/ai/conversations",
        headers=admin_headers,
        json={"title": "新会话", "source": "mobile"},
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    payload = "ERROR upstream timeout while connecting to database"
    data_url = "data:text/plain;base64," + base64.b64encode(payload.encode("utf-8")).decode("ascii")
    uploaded = client.post(
        "/api/v1/ai/files/upload",
        headers=admin_headers,
        json={
            "conversation_id": conversation_id,
            "name": "backend-error.log",
            "type": "text/plain",
            "size": len(payload.encode("utf-8")),
            "data_url": data_url,
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    uploaded_file = uploaded.json()["file"]

    resp = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={
            "conversation_id": conversation_id,
            "message": "请分析附件里的报错原因",
            "attachments": [
                {
                    "file_id": uploaded_file["file_id"],
                    "name": uploaded_file["name"],
                    "type": uploaded_file["type"],
                    "size": uploaded_file["size"],
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tool_calls"][0]["tool"] == "analyze_log_text"
    assert body["reply"]

    detail = client.get(f"/api/v1/ai/conversations/{conversation_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["message_count"] == 2


def test_ai_file_upload_decodes_gbk_csv(client, admin_headers):
    import base64

    created = client.post(
        "/api/v1/ai/conversations",
        headers=admin_headers,
        json={"title": "CSV日志分析", "source": "mobile"},
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    payload = "时间,级别,内容\n2026-06-10 10:00:00,ERROR,数据库连接失败\n"
    raw = payload.encode("gbk")
    data_url = "data:text/csv;base64," + base64.b64encode(raw).decode("ascii")
    uploaded = client.post(
        "/api/v1/ai/files/upload",
        headers=admin_headers,
        json={
            "conversation_id": conversation_id,
            "name": "system-error.csv",
            "type": "text/csv",
            "size": len(raw),
            "data_url": data_url,
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()["file"]
    assert "数据库连接失败" in body["extracted_text"]
    assert "���" not in body["extracted_text"]
