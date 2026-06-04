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


def test_admin_asset_update_and_retire(client, admin_headers):
    create = client.post(
        "/api/v1/admin/assets",
        headers=admin_headers,
        json={"asset_code": "ASSET-EDIT-001", "name": "待编辑资产", "category": "server", "system_id": 1},
    )
    assert create.status_code == 200, create.text
    asset_id = create.json()["id"]

    update = client.put(
        f"/api/v1/admin/assets/{asset_id}",
        headers=admin_headers,
        json={"name": "已编辑资产", "ip_address": "10.9.8.7", "port": 443, "status": "repair"},
    )
    assert update.status_code == 200, update.text

    listing = client.get("/api/v1/admin/assets?keyword=ASSET-EDIT-001", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    item = listing.json()["items"][0]
    assert item["name"] == "已编辑资产"
    assert item["ip_address"] == "10.9.8.7"
    assert item["port"] == 443
    assert item["status"] == "repair"

    retire = client.delete(f"/api/v1/admin/assets/{asset_id}", headers=admin_headers)
    assert retire.status_code == 200, retire.text
    assert retire.json()["status"] == "retired"


def test_admin_asset_rejects_missing_shared_refs(client, admin_headers):
    create = client.post(
        "/api/v1/admin/assets",
        headers=admin_headers,
        json={"asset_code": "ASSET-BAD-REF-001", "name": "错误引用资产", "category": "server", "room_id": 999999},
    )
    assert create.status_code == 400
    assert create.json()["code"] == "ROOM_NOT_FOUND"
