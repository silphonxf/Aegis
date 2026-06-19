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


def test_admin_inspection_record_review_returns_display_fields(client, admin_headers):
    room = client.post(
        "/api/v1/admin/rooms",
        headers=admin_headers,
        json={
            "room_code": "ROOM-REVIEW-001",
            "room_name": "审阅机房",
            "qr_content": "QR://ROOM-REVIEW-001",
            "check_items": ["温湿度", "门禁状态"],
        },
    )
    assert room.status_code == 200, room.text
    room_id = room.json()["id"]

    point = client.post(
        "/api/v1/admin/inspection-points",
        headers=admin_headers,
        json={
            "room_id": room_id,
            "point_code": "POINT-REVIEW-001",
            "point_name": "审阅点位",
            "point_type": "qr",
            "qr_content": "QR://POINT-REVIEW-001",
        },
    )
    assert point.status_code == 200, point.text
    point_id = point.json()["id"]

    record = client.post(
        "/api/v1/inspections/records",
        headers=admin_headers,
        json={
            "system_id": 1,
            "point_id": point_id,
            "room_id": room_id,
            "result": "abnormal",
            "note": "温度偏高",
            "check_results": [{"item": "温湿度", "result": "abnormal"}, {"item": "门禁状态", "result": "normal"}],
            "monitoring_confirmation": "monitoring_no_alarm",
            "source": "qr",
            "inspected_at": "2026-06-18T10:30:00",
        },
    )
    assert record.status_code == 200, record.text

    review = client.get(
        "/api/v1/admin/inspection-records",
        headers=admin_headers,
        params={"room_id": room_id, "result": "abnormal"},
    )
    assert review.status_code == 200, review.text
    target = next(item for item in review.json()["items"] if item["id"] == record.json()["id"])
    assert target["room_name"] == "审阅机房"
    assert target["point_name"] == "审阅点位"
    assert target["system_name"] == "示例业务系统"
    assert target["inspector_name"] == "admin"
    assert target["note"] == "温度偏高"
    assert target["check_results"][0]["item"] == "温湿度"
    assert target["monitoring_confirmation"] == "monitoring_no_alarm"
