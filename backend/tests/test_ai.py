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
