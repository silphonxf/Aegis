from pathlib import Path


class FakeOpenClawClient:
    def __init__(self):
        self.messages = []

    def is_configured(self):
        return True

    def chat(self, *, message, conversation_id=None, attachments=None, history=None, summary=None):
        self.messages.append(message)
        return {
            "conversation_id": conversation_id or "fake-openclaw",
            "summary": "MySQL 自检正常",
            "reply": "总体结论：数据库连接数正常，未发现死锁。",
            "suggestions": ["继续观察连接池使用率。"],
        }


def test_create_template_and_list(client, admin_headers):
    create = client.post(
        "/api/v1/selfchecks/templates",
        headers=admin_headers,
        json={"system_id": 1, "check_type": "daily", "name": "默认日检模板"},
    )
    assert create.status_code == 200, create.text
    tpl_id = create.json()["id"]
    assert tpl_id > 0

    listing = client.get("/api/v1/selfchecks/templates", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == tpl_id for item in listing.json()["items"])


def test_create_simple_selfcheck_record_auto_template(client, admin_headers):
    create = client.post(
        "/api/v1/selfchecks/records/simple",
        headers=admin_headers,
        json={"content": "CPU/MEM/DISK 正常", "result": "normal", "note": "自动回归"},
    )
    assert create.status_code == 200, create.text
    body = create.json()
    assert body["id"] > 0
    assert body["system_id"] == 1
    assert body["template_id"] > 0

    listing = client.get("/api/v1/selfchecks/records", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == body["id"] for item in listing.json()["items"])


def test_run_system_selfcheck_without_skill_returns_status_and_no_ai(client, admin_headers):
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={"system_code": "SYS-SC-NO-SKILL", "name": "无AI自检系统", "host_address": "10.1.2.3", "env": "prod"},
    )
    assert created.status_code == 200, created.text
    system_id = created.json()["id"]

    snapshot = client.post(
        f"/api/v1/systems/{system_id}/status/snapshot",
        headers=admin_headers,
        json={
            "host_online": "normal",
            "port_ok": "normal",
            "cpu_usage": 91,
            "mem_usage": 40,
            "disk_usage": 50,
            "last_inspection_result": "normal",
            "last_selfcheck_result": "unknown",
        },
    )
    assert snapshot.status_code == 200, snapshot.text

    resp = client.get(f"/api/v1/selfchecks/run?system_id={system_id}&range_minutes=60", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["system"]["system_id"] == system_id
    assert body["system"]["selfcheck_skill"] is None
    assert body["status"]["latest"]["cpu_usage"] == 91
    assert body["alarms"]
    assert body["report_file"]["alarm_count"] == len(body["alarms"])
    assert body["ai_report"] is None

    snapshot2 = client.post(
        f"/api/v1/systems/{system_id}/status/snapshot",
        headers=admin_headers,
        json={
            "host_online": "normal",
            "port_ok": "normal",
            "cpu_usage": 37,
            "mem_usage": 42,
            "disk_usage": 55,
            "last_inspection_result": "normal",
            "last_selfcheck_result": "unknown",
        },
    )
    assert snapshot2.status_code == 200, snapshot2.text

    status = client.get(f"/api/v1/selfchecks/status?system_id={system_id}&range_minutes=60", headers=admin_headers)
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["status"]["latest"]["cpu_usage"] == 37
    assert status_body["alarm_count"] >= 1

    reports = client.get(f"/api/v1/selfchecks/reports?system_id={system_id}", headers=admin_headers)
    assert reports.status_code == 200, reports.text
    report_items = reports.json()["items"]
    assert report_items
    assert report_items[0]["alarm_count"] == len(body["alarms"])

    detail = client.get(f"/api/v1/selfchecks/reports/{report_items[0]['file_name']}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["system"]["system_id"] == system_id
    assert detail_body["alarm_count"] == len(body["alarms"])
    assert detail_body["alarms"]
    report_path = detail_body.get("report_file", {}).get("file_path")
    if report_path:
        Path(report_path).unlink(missing_ok=True)


def test_run_system_selfcheck_uses_local_report_instead_of_chat_fallback(client, admin_headers):
    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-SC-LOCAL-REPORT",
            "name": "正常自检系统",
            "host_address": "10.2.3.4",
            "env": "prod",
            "selfcheck_skill": "检查 CPU、内存、硬盘、主机在线和端口状态，输出结论与处理建议。",
        },
    )
    assert created.status_code == 200, created.text
    system_id = created.json()["id"]

    snapshot = client.post(
        f"/api/v1/systems/{system_id}/status/snapshot",
        headers=admin_headers,
        json={
            "host_online": "normal",
            "port_ok": "normal",
            "cpu_usage": 33,
            "mem_usage": 44,
            "disk_usage": 55,
            "last_inspection_result": "normal",
            "last_selfcheck_result": "unknown",
        },
    )
    assert snapshot.status_code == 200, snapshot.text

    resp = client.get(f"/api/v1/selfchecks/run?system_id={system_id}&range_minutes=60", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    report = body["ai_report"]
    assert report["mode"] == "selfcheck_local"
    assert report["fallback_reason"] is None
    assert "当前仍使用本地 fallback 规则回复" not in report["reply"]
    assert "关键指标" in report["reply"]
    assert "处理建议" in report["reply"]

    report_path = body.get("report_file", {}).get("file_path")
    if report_path:
        Path(report_path).unlink(missing_ok=True)


def test_mysql_selfcheck_collects_db_status_and_sends_redacted_prompt_to_openclaw(monkeypatch, client, admin_headers):
    from app.api import selfchecks

    fake_openclaw = FakeOpenClawClient()
    monkeypatch.setattr(selfchecks, "openclaw_client", fake_openclaw)
    monkeypatch.setattr(
        selfchecks,
        "_collect_mysql_status",
        lambda system: {
            "ok": True,
            "target": {"host": "127.0.0.1", "port": 3306, "database": "aegis", "user": "aegis_user"},
            "global_status": [
                {"Variable_name": "Threads_connected", "Value": "3"},
                {"Variable_name": "Threads_running", "Value": "1"},
            ],
            "variables": [{"Variable_name": "max_connections", "Value": "151"}],
            "innodb_status": {"latest_detected_deadlock": "未发现最近死锁片段。"},
        },
    )

    created = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "MYSQL-LOCAL-001",
            "name": "本地mysql数据库",
            "host_address": "127.0.0.1",
            "env": "prod",
            "selfcheck_skill": "本地mysql数据库是aegis用户：aegis_user密码：DummyPass#2026，帮我看下数据库是否正常",
        },
    )
    assert created.status_code == 200, created.text
    system_id = created.json()["id"]

    resp = client.get(f"/api/v1/selfchecks/run?system_id={system_id}&range_minutes=60", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    report = body["ai_report"]
    assert report["mode"] == "openclaw_mysql_selfcheck"
    assert report["mysql_status"]["global_status"][0]["Variable_name"] == "Threads_connected"
    assert "数据库连接数正常" in report["reply"]
    assert fake_openclaw.messages
    assert "Threads_connected" in fake_openclaw.messages[0]
    assert "DummyPass#2026" not in fake_openclaw.messages[0]
    assert "密码：******" in fake_openclaw.messages[0]
    assert "CPU=" not in fake_openclaw.messages[0]

    report_path = body.get("report_file", {}).get("file_path")
    if report_path:
        Path(report_path).unlink(missing_ok=True)


def test_mysql_selfcheck_redacts_collected_status_strings():
    from app.api import selfchecks

    redacted = selfchecks._redact_collected_status({
        "processlist": [{"INFO": "ALTER USER 'aegis_user' IDENTIFIED BY 'DummyPass#2026'"}],
        "note": "password=DummyPass#2026",
        "skill": "密码：DummyPass#2026",
    })

    dumped = str(redacted)
    assert "DummyPass#2026" not in dumped
    assert "******" in dumped
