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


def test_capture_url_normalizes_chinese_path_and_query():
    from app.api.toolbox import _normalize_capture_url

    normalized = _normalize_capture_url("https://example.com/接口/登录?备注=登录失败&x=1")

    assert normalized == "https://example.com/%E6%8E%A5%E5%8F%A3/%E7%99%BB%E5%BD%95?%E5%A4%87%E6%B3%A8=%E7%99%BB%E5%BD%95%E5%A4%B1%E8%B4%A5&x=1"
    normalized.encode("ascii")


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


def test_toolbox_error_logs_reads_configured_system_log_path(client, admin_headers, tmp_path):
    log_file = tmp_path / "configured-system.log"
    log_file.write_text(
        "2026-06-04 12:00:00 INFO app normal\n"
        "2026-06-04 12:01:00 ERROR app configured path failed\n",
        encoding="utf-8",
    )
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-LOG-CONFIG-001",
            "name": "日志配置系统",
            "host_address": "127.0.0.1",
            "env": "prod",
            "log_configs": [{"log_name": "configured", "absolute_path": str(log_file), "log_level": "error"}],
        },
    )
    assert created.status_code == 200, created.text

    resp = client.get(
        "/api/v1/toolbox/error-logs",
        headers=admin_headers,
        params={"source": "system", "file_name": str(log_file), "level": "error", "lines": 20},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "configured path failed" in body["content"]
    assert str(log_file) in body["source_detail"]


def test_toolbox_error_logs_all_range_reads_whole_selected_file_window(client, admin_headers, tmp_path):
    log_file = tmp_path / "full-range-system.log"
    log_file.write_text(
        "2026-01-01 00:00:00 ERROR app first historical failure\n"
        "2026-06-04 12:00:00 INFO app normal\n"
        "2026-12-31 23:59:59 ERROR app future scheduled failure\n",
        encoding="utf-8",
    )
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-LOG-FULL-RANGE-001",
            "name": "全量日志系统",
            "host_address": "127.0.0.1",
            "env": "prod",
            "log_configs": [{"log_name": "full-range", "absolute_path": str(log_file), "log_level": "error"}],
        },
    )
    assert created.status_code == 200, created.text

    resp = client.get(
        "/api/v1/toolbox/error-logs",
        headers=admin_headers,
        params={"source": "system", "file_name": str(log_file), "quick_range": "all", "level": "error", "lines": 10000},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["quick_range"] == "all"
    assert body["range_mode"] == "all_file"
    assert "first historical failure" in body["content"]
    assert "future scheduled failure" in body["content"]


def test_toolbox_error_logs_error_level_includes_http_exception_warning(client, admin_headers, tmp_path):
    log_file = tmp_path / "http-exception-system.log"
    log_file.write_text(
        "2026-06-10 13:50:34 WARNING app [req:abc] HTTP 异常: method=POST path=/api/v1/assistant/chat status=400 code=CAPTURE_FETCH_FAILED message=抓取失败：HTTP 502\n",
        encoding="utf-8",
    )
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-LOG-HTTP-EXCEPTION-001",
            "name": "HTTP异常日志系统",
            "host_address": "127.0.0.1",
            "env": "prod",
            "log_configs": [{"log_name": "http-exception", "absolute_path": str(log_file), "log_level": "error"}],
        },
    )
    assert created.status_code == 200, created.text

    resp = client.get(
        "/api/v1/toolbox/error-logs",
        headers=admin_headers,
        params={"source": "system", "file_name": str(log_file), "level": "error", "lines": 20},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "抓取失败：HTTP 502" in body["content"]


def test_toolbox_error_logs_error_level_does_not_match_query_param_text(client, admin_headers, tmp_path):
    log_file = tmp_path / "query-param-only.log"
    log_file.write_text(
        '2026-06-10 13:56:48 INFO access [req:-] "GET /api/v1/toolbox/error-logs?level=error&lines=100 HTTP/1.1" 200\n',
        encoding="utf-8",
    )
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-LOG-QUERY-PARAM-001",
            "name": "查询参数日志系统",
            "host_address": "127.0.0.1",
            "env": "prod",
            "log_configs": [{"log_name": "query-param", "absolute_path": str(log_file), "log_level": "error"}],
        },
    )
    assert created.status_code == 200, created.text

    resp = client.get(
        "/api/v1/toolbox/error-logs",
        headers=admin_headers,
        params={"source": "system", "file_name": str(log_file), "level": "error", "lines": 20},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "level=error" not in body["content"]
    assert "未读取到系统日志" in body["content"]


def test_toolbox_error_logs_warning_does_not_fallback_to_info(client, admin_headers, tmp_path):
    log_file = tmp_path / "info-only-system.log"
    log_file.write_text(
        "2026-06-04 12:00:00 INFO app normal startup\n"
        "2026-06-04 12:01:00 INFO app regular heartbeat\n",
        encoding="utf-8",
    )
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-LOG-INFO-ONLY-001",
            "name": "仅 INFO 日志系统",
            "host_address": "127.0.0.1",
            "env": "prod",
            "log_configs": [{"log_name": "info-only", "absolute_path": str(log_file), "log_level": "info"}],
        },
    )
    assert created.status_code == 200, created.text

    resp = client.get(
        "/api/v1/toolbox/error-logs",
        headers=admin_headers,
        params={"source": "system", "file_name": str(log_file), "level": "warning", "lines": 20},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "regular heartbeat" not in body["content"]
    assert "未读取到系统日志" in body["content"]
