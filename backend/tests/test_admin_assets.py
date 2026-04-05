def test_admin_asset_create_list_summary_export(client, admin_headers):
    create = client.post(
        "/api/v1/admin/assets",
        headers=admin_headers,
        json={
            "asset_code": "ASSET-001",
            "name": "测试服务器",
            "category": "server",
            "system_id": 1,
            "location": "机房A",
            "status": "in_use",
        },
    )
    assert create.status_code == 200, create.text
    asset_id = create.json()["id"]
    assert asset_id > 0

    listing = client.get("/api/v1/admin/assets?page=1&size=20", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == asset_id for item in listing.json()["items"])

    summary = client.get("/api/v1/admin/assets/summary", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["total"] >= 1

    export_resp = client.get("/api/v1/admin/assets/export", headers=admin_headers)
    assert export_resp.status_code == 200
    assert "asset_code" in export_resp.text


def test_admin_asset_batch_create_with_skip(client, admin_headers):
    batch = client.post(
        "/api/v1/admin/assets/batch",
        headers=admin_headers,
        json={
            "items": [
                {"asset_code": "ASSET-B-001", "name": "批量1", "category": "server", "system_id": 1, "status": "in_use"},
                {"asset_code": "ASSET-B-001", "name": "批量重复", "category": "server", "system_id": 1, "status": "in_use"},
                {"asset_code": "ASSET-B-002", "name": "批量2", "category": "network", "system_id": 1, "status": "repair"}
            ]
        },
    )
    assert batch.status_code == 200, batch.text
    body = batch.json()
    assert len(body["created"]) == 2
    assert len(body["skipped"]) == 1
