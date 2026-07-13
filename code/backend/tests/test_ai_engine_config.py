def test_ai_engine_chat_uses_page_config(client, admin_headers, monkeypatch):
    from app.api import admin as admin_api

    captured = {}

    def fake_run_chat(payload, history=None, summary=None, runtime_config=None):
        captured["message"] = payload.message
        captured["history"] = history
        captured["config"] = runtime_config
        return {
            "conversation_id": "config-test-1",
            "mode": "pi_gateway",
            "summary": "Pi Gateway response",
            "reply": "页面配置测试成功",
            "severity": "medium",
            "suggestions": [],
            "attachment_notes": [],
            "elapsed_ms": 12,
            "fallback_reason": None,
        }

    monkeypatch.setattr(admin_api, "get_runtime_ai_config", lambda: {"api_key": "saved-secret"})
    monkeypatch.setattr(admin_api, "run_chat", fake_run_chat)

    response = client.post(
        "/api/v1/admin/ai-engine-config/test-chat",
        headers=admin_headers,
        json={
            "message": "测试页面配置",
            "conversation_id": "config-test-1",
            "history": [{"role": "user", "content": "上一轮问题"}],
            "engine_type": "pi_gateway",
            "base_url": "https://pi.example.test",
            "api_key": None,
            "model": "qwen-plus",
            "timeout_seconds": 90,
            "chat_path": "/v1/messages",
            "diagnose_path": "/v1/messages",
            "log_analyze_path": "/v1/messages",
            "enabled": True,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["tested_engine_type"] == "pi_gateway"
    assert response.json()["mode"] == "pi_gateway"
    assert captured["message"] == "测试页面配置"
    assert captured["history"] == [{"role": "user", "content": "上一轮问题"}]
    assert captured["config"] == {
        "engine_type": "pi_gateway",
        "base_url": "https://pi.example.test",
        "api_key": "saved-secret",
        "model": "qwen-plus",
        "timeout_seconds": 90,
        "chat_path": "/v1/messages",
        "diagnose_path": "/v1/messages",
        "log_analyze_path": "/v1/messages",
        "enabled": True,
    }
