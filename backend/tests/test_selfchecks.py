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
