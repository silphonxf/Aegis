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
    assert body["ai_report"] is None
