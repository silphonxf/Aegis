def test_admin_create_and_list_systems(client, admin_headers):
    create = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-TEST-001",
            "name": "测试系统",
            "host_address": "192.168.10.11",
            "env": "test",
            "owner_user_ids": [1],
            "check_frequency": "daily",
            "log_configs": [
                {"log_name": "app-error", "absolute_path": "/var/log/aegis/app-error.log", "log_level": "error"},
                {"log_name": "access", "absolute_path": "/var/log/nginx/access.log", "log_level": "info"},
            ],
        },
    )
    assert create.status_code == 200, create.text
    system_id = create.json()["id"]
    assert system_id > 0

    listing = client.get(
        "/api/v1/admin/systems?page=1&size=50&keyword=192.168.10&env=test&sort_by=host_address&sort_order=asc",
        headers=admin_headers,
    )
    assert listing.status_code == 200, listing.text
    target = next(item for item in listing.json()["items"] if item["id"] == system_id)
    assert target["host_address"] == "192.168.10.11"
    assert target["check_frequency"] == "daily"
    assert 1 in target["owner_user_ids"]
    assert [item["absolute_path"] for item in target["log_configs"]] == [
        "/var/log/aegis/app-error.log",
        "/var/log/nginx/access.log",
    ]


def test_admin_update_and_deactivate_system(client, admin_headers):
    create = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={"system_code": "SYS-EDIT-001", "name": "待编辑系统", "env": "test", "owner_user_ids": [1]},
    )
    assert create.status_code == 200, create.text
    system_id = create.json()["id"]

    update = client.put(
        f"/api/v1/admin/systems/{system_id}",
        headers=admin_headers,
        json={
            "name": "已编辑系统",
            "host_address": "10.20.30.40",
            "env": "prod",
            "owner_user_ids": [],
            "check_frequency": "weekly",
            "log_configs": [{"log_name": "secure", "absolute_path": "/var/log/secure", "log_level": "warning"}],
        },
    )
    assert update.status_code == 200, update.text

    listing = client.get("/api/v1/admin/systems?page=1&size=100", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    target = next(item for item in listing.json()["items"] if item["id"] == system_id)
    assert target["name"] == "已编辑系统"
    assert target["host_address"] == "10.20.30.40"
    assert target["env"] == "prod"
    assert target["owner_user_ids"] == []
    assert target["check_frequency"] == "weekly"
    assert len(target["log_configs"]) == 1
    assert target["log_configs"][0]["absolute_path"] == "/var/log/secure"

    deactivate = client.delete(f"/api/v1/admin/systems/{system_id}", headers=admin_headers)
    assert deactivate.status_code == 200, deactivate.text
    assert deactivate.json()["is_active"] is False


def test_system_log_path_requires_absolute_path(client, admin_headers):
    create = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-REL-001",
            "name": "相对路径系统",
            "env": "test",
            "log_configs": [{"log_name": "bad", "absolute_path": "logs/app.log"}],
        },
    )
    assert create.status_code == 422, create.text


def test_accessible_systems_and_log_configs_are_owner_scoped(client, admin_headers):
    user_resp = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={"username": "ops_user", "password": "ops_user_pass", "role_code": "inspector"},
    )
    assert user_resp.status_code == 200, user_resp.text
    user_id = user_resp.json()["id"]

    owned = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={
            "system_code": "SYS-OWNED-001",
            "name": "归属系统",
            "host_address": "172.16.1.10",
            "env": "prod",
            "owner_user_ids": [user_id],
            "log_configs": [{"log_name": "owned", "absolute_path": "/data/app/logs/owned.log"}],
        },
    )
    assert owned.status_code == 200, owned.text
    owned_id = owned.json()["id"]
    other = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={"system_code": "SYS-OTHER-001", "name": "其他系统", "host_address": "172.16.1.11", "env": "prod"},
    )
    assert other.status_code == 200, other.text
    other_id = other.json()["id"]

    login = client.post("/api/v1/auth/login", json={"username": "ops_user", "password": "ops_user_pass"})
    assert login.status_code == 200, login.text
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    accessible = client.get("/api/v1/systems/accessible", headers=user_headers)
    assert accessible.status_code == 200, accessible.text
    assert [item["system_id"] for item in accessible.json()["items"]] == [owned_id]

    logs = client.get(f"/api/v1/systems/{owned_id}/log-configs", headers=user_headers)
    assert logs.status_code == 200, logs.text
    assert logs.json()["host_address"] == "172.16.1.10"
    assert logs.json()["items"][0]["absolute_path"] == "/data/app/logs/owned.log"

    denied = client.get(f"/api/v1/systems/{other_id}/log-configs", headers=user_headers)
    assert denied.status_code == 404, denied.text
