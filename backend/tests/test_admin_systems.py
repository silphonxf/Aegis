def test_admin_create_and_list_systems(client, admin_headers):
    create = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={"system_code": "SYS-TEST-001", "name": "测试系统", "env": "test"},
    )
    assert create.status_code == 200, create.text
    system_id = create.json()["id"]
    assert system_id > 0

    listing = client.get("/api/v1/admin/systems?page=1&size=50", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == system_id for item in listing.json()["items"])
