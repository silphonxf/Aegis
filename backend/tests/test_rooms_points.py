def test_create_and_list_rooms(client, admin_headers):
    create = client.post(
        "/api/v1/admin/rooms",
        headers=admin_headers,
        json={"room_code": "ROOM-TEST-001", "room_name": "测试机房", "building": "A座", "floor": "3F"},
    )
    assert create.status_code == 200, create.text
    room_id = create.json()["id"]
    assert room_id > 0

    listing = client.get("/api/v1/admin/rooms", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    data = listing.json()
    assert data["total"] >= 1
    assert any(item["id"] == room_id and item["is_active"] is True for item in data["items"])


def test_create_and_list_inspection_points(client, admin_headers):
    room = client.post(
        "/api/v1/admin/rooms",
        headers=admin_headers,
        json={"room_code": "ROOM-TEST-002", "room_name": "巡检机房"},
    )
    assert room.status_code == 200, room.text
    room_id = room.json()["id"]

    create = client.post(
        "/api/v1/admin/inspection-points",
        headers=admin_headers,
        json={
            "room_id": room_id,
            "system_id": 1,
            "point_code": "POINT-TEST-001",
            "point_name": "测试点位",
            "point_type": "qr",
            "qr_content": "QR://POINT-TEST-001",
            "location_detail": "A区机柜1",
            "is_active": True,
        },
    )
    assert create.status_code == 200, create.text
    point_id = create.json()["id"]
    assert point_id > 0

    listing = client.get("/api/v1/admin/inspection-points", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == point_id and item["room_id"] == room_id for item in listing.json()["items"])


def test_create_inspection_point_can_be_room_only(client, admin_headers):
    room = client.post(
        "/api/v1/admin/rooms",
        headers=admin_headers,
        json={"room_code": "ROOM-ONLY-001", "room_name": "无系统点位机房"},
    )
    assert room.status_code == 200, room.text

    create = client.post(
        "/api/v1/admin/inspection-points",
        headers=admin_headers,
        json={
            "room_id": room.json()["id"],
            "point_code": "POINT-ROOM-ONLY-001",
            "point_name": "只绑定机房点位",
            "point_type": "qr",
            "location_detail": "B区入口",
        },
    )
    assert create.status_code == 200, create.text

    listing = client.get("/api/v1/admin/inspection-points", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    item = next(item for item in listing.json()["items"] if item["id"] == create.json()["id"])
    assert item["system_id"] is None
    assert item["qr_content"] == "POINT-ROOM-ONLY-001"


def test_create_inspection_point_rejects_missing_room(client, admin_headers):
    create = client.post(
        "/api/v1/admin/inspection-points",
        headers=admin_headers,
        json={
            "room_id": 999999,
            "point_code": "POINT-NO-ROOM-001",
            "point_name": "不存在机房点位",
        },
    )
    assert create.status_code == 400
    assert create.json()["code"] == "ROOM_NOT_FOUND"


def test_asset_shared_fields_are_returned_and_exported(client, admin_headers):
    room = client.post(
        "/api/v1/admin/rooms",
        headers=admin_headers,
        json={"room_code": "ROOM-ASSET-001", "room_name": "资产机房"},
    )
    assert room.status_code == 200, room.text
    room_id = room.json()["id"]

    create = client.post(
        "/api/v1/admin/assets",
        headers=admin_headers,
        json={
            "asset_code": "ASSET-SHARED-001",
            "name": "共享资产",
            "category": "server",
            "room_id": room_id,
            "ip_address": "10.1.2.3",
            "port": 22,
            "connection_type": "ssh",
            "remark": "for shared data test",
        },
    )
    assert create.status_code == 200, create.text

    listing = client.get("/api/v1/admin/assets?keyword=ASSET-SHARED-001", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    item = listing.json()["items"][0]
    assert item["room_id"] == room_id
    assert item["ip_address"] == "10.1.2.3"
    assert item["port"] == 22
    assert item["connection_type"] == "ssh"
    assert item["remark"] == "for shared data test"

    export = client.get("/api/v1/admin/assets/export?keyword=ASSET-SHARED-001", headers=admin_headers)
    assert export.status_code == 200, export.text
    assert "room_id" in export.text
    assert "10.1.2.3" in export.text


def test_update_and_deactivate_room(client, admin_headers):
    create = client.post(
        "/api/v1/admin/rooms",
        headers=admin_headers,
        json={"room_code": "ROOM-EDIT-001", "room_name": "待编辑机房"},
    )
    assert create.status_code == 200, create.text
    room_id = create.json()["id"]

    update = client.put(
        f"/api/v1/admin/rooms/{room_id}",
        headers=admin_headers,
        json={"room_name": "已编辑机房", "building": "B座", "floor": "9F"},
    )
    assert update.status_code == 200, update.text

    listing = client.get("/api/v1/admin/rooms?include_inactive=true", headers=admin_headers)
    target = next(item for item in listing.json()["items"] if item["id"] == room_id)
    assert target["room_name"] == "已编辑机房"
    assert target["building"] == "B座"
    assert target["floor"] == "9F"

    deactivate = client.delete(f"/api/v1/admin/rooms/{room_id}", headers=admin_headers)
    assert deactivate.status_code == 200, deactivate.text
    assert deactivate.json()["is_active"] is False

    active_listing = client.get("/api/v1/admin/rooms", headers=admin_headers)
    assert all(item["id"] != room_id for item in active_listing.json()["items"])


def test_update_and_deactivate_inspection_point(client, admin_headers):
    room = client.post(
        "/api/v1/admin/rooms",
        headers=admin_headers,
        json={"room_code": "ROOM-POINT-EDIT-001", "room_name": "点位编辑机房"},
    )
    assert room.status_code == 200, room.text

    create = client.post(
        "/api/v1/admin/inspection-points",
        headers=admin_headers,
        json={
            "room_id": room.json()["id"],
            "point_code": "POINT-EDIT-001",
            "point_name": "待编辑点位",
            "location_detail": "旧位置",
        },
    )
    assert create.status_code == 200, create.text
    point_id = create.json()["id"]

    update = client.put(
        f"/api/v1/admin/inspection-points/{point_id}",
        headers=admin_headers,
        json={"point_name": "已编辑点位", "qr_content": "QR://POINT-EDIT-001", "location_detail": "新位置"},
    )
    assert update.status_code == 200, update.text

    listing = client.get("/api/v1/admin/inspection-points", headers=admin_headers)
    target = next(item for item in listing.json()["items"] if item["id"] == point_id)
    assert target["point_name"] == "已编辑点位"
    assert target["qr_content"] == "QR://POINT-EDIT-001"
    assert target["location_detail"] == "新位置"

    deactivate = client.delete(f"/api/v1/admin/inspection-points/{point_id}", headers=admin_headers)
    assert deactivate.status_code == 200, deactivate.text
    assert deactivate.json()["is_active"] is False
