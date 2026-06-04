from app.api import toolbox


def test_toolbox_ping_and_port_check(client, admin_headers):
    ping = client.post(
        "/api/v1/toolbox/ping",
        headers=admin_headers,
        json={"host": "127.0.0.1", "count": 1},
    )
    assert ping.status_code == 200, ping.text
    assert ping.json()["host"] == "127.0.0.1"

    port = client.post(
        "/api/v1/toolbox/port-check",
        headers=admin_headers,
        json={"host": "127.0.0.1", "port": 65535, "timeout_ms": 100},
    )
    assert port.status_code == 200, port.text
    assert port.json()["port"] == 65535


def test_toolbox_restart_task_status_flow(client, admin_headers):
    create = client.post(
        "/api/v1/toolbox/restart-task",
        headers=admin_headers,
        json={"target": "local-host", "reason": "pytest"},
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["id"]

    approve = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "approved", "note": "ok"},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"

    running = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "running", "note": "started", "executor": "manual"},
    )
    assert running.status_code == 200, running.text
    assert running.json()["status"] == "running"

    done = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "done", "note": "finished", "executor": "manual"},
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "done"
    assert done.json()["result"]["success"] is True


def test_toolbox_invalid_status_transition(client, admin_headers):
    create = client.post(
        "/api/v1/toolbox/restart-task",
        headers=admin_headers,
        json={"target": "local-host", "reason": "pytest-invalid"},
    )
    task_id = create.json()["id"]

    invalid = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "done", "note": "skip approval"},
    )
    assert invalid.status_code == 400, invalid.text
    assert invalid.json()["code"] == "TASK_STATUS_INVALID"

    approve = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "approved", "note": "ok"},
    )
    assert approve.status_code == 200, approve.text

    invalid2 = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "rejected", "note": "cannot reject after approve"},
    )
    assert invalid2.status_code == 400, invalid2.text
    assert invalid2.json()["code"] == "TASK_STATUS_INVALID"


def test_toolbox_capture_fetch_invalid_url(client, admin_headers):
    resp = client.post(
        "/api/v1/toolbox/capture/fetch",
        headers=admin_headers,
        json={"url": "not a valid url"},
    )
    assert resp.status_code == 400, resp.text


def test_toolbox_capture_analyze(client, admin_headers):
    resp = client.post(
        "/api/v1/toolbox/capture/analyze",
        headers=admin_headers,
        json={
            "title": "抓包结果分析",
            "content": "10:00:01 upstream connect timeout while TLS handshake\n10:00:03 read timeout from gateway",
            "severity": "medium",
            "source": "tcpdump_excerpt",
            "note": "登录接口偶发超时",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "抓包结果分析"
    assert body["mode"] in {"rule_fallback", "openclaw", "offline_ollama"}
    assert body["severity"] in {"medium", "high"}
    assert isinstance(body["suggestions"], list)
    assert "timeout" in body["excerpt"].lower()


def test_toolbox_error_logs_accepts_aegis_https_alias(client, admin_headers, monkeypatch, tmp_path):
    log_file = tmp_path / "backend-https.log"
    log_file.write_text(
        "2026-06-03 10:00:00 INFO app [req:-] Aegis API 启动\n"
        "2026-06-03 10:01:00 WARNING app [req:-] 示例告警\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(toolbox, "_collect_log_files", lambda source: [str(log_file)] if source == "aegis" else [])

    resp = client.get(
        "/api/v1/toolbox/error-logs?source=aegis&file_name=aegis-backend-https.log&level=warning&lines=20",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "示例告警" in body["content"]
    assert "backend-https.log" in body["source_detail"]
