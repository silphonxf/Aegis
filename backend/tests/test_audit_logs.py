def test_audit_logs_can_be_filtered(client, admin_headers):
    client.post(
        "/api/v1/admin/assets",
        headers=admin_headers,
        json={
            "asset_code": "AUDIT-ASSET-001",
            "name": "审计测试资产",
            "category": "server",
            "system_id": 1,
            "location": "机房B",
            "status": "in_use",
        },
    )

    resp = client.get(
        "/api/v1/admin/audit-logs?page=1&size=20&action=create_asset",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["action"] == "create_asset" for item in body["items"])
