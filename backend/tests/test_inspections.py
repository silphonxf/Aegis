from datetime import datetime, timezone


def test_resolve_point_by_system_id_qr(client, admin_headers):
    resp = client.get("/api/v1/inspections/points/resolve", params={"qr_content": "1"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["system_id"] == 1
    assert body["point_code"] == "P-001"


def test_resolve_point_by_legacy_qr_content(client, admin_headers):
    resp = client.get(
        "/api/v1/inspections/points/resolve",
        params={"qr_content": "QR://DEMO-SYS-001/P-001"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["system_name"] == "示例业务系统"


def test_create_and_list_inspection_record(client, admin_headers):
    create = client.post(
        "/api/v1/inspections/records",
        headers=admin_headers,
        json={
            "system_id": 1,
            "point_id": 1,
            "result": "normal",
            "note": "smoke test",
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert create.status_code == 200, create.text
    record_id = create.json()["id"]
    assert record_id > 0

    listing = client.get("/api/v1/inspections/records", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == record_id for item in listing.json()["items"])
