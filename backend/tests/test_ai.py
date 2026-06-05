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
