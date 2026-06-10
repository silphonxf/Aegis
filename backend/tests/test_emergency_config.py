def test_emergency_config_visible_to_mobile_and_creates_task(client, admin_headers):
    system_resp = client.post(
        "/api/v1/admin/systems",
        headers=admin_headers,
        json={"system_code": "EMG-SYS-001", "name": "应急测试系统", "host_address": "10.0.0.10", "env": "prod"},
    )
    assert system_resp.status_code == 200, system_resp.text
    system_id = system_resp.json()["id"]

    host_resp = client.post(
        "/api/v1/admin/emergency-config/ssh-hosts",
        headers=admin_headers,
        json={
            "host_code": "emg-host-01",
            "host_name": "应急主机01",
            "host_ip": "10.0.0.10",
            "port": 22,
            "username": "ops",
            "auth_type": "password",
            "password_plaintext": "secret-once",
            "connect_timeout_ms": 5000,
            "system_id": system_id,
            "enabled": True,
        },
    )
    assert host_resp.status_code == 200, host_resp.text
    assert host_resp.json()["password_ciphertext"] == "***"
    assert host_resp.json()["has_password"] is True

    action_resp = client.post(
        "/api/v1/admin/emergency-config/server-actions",
        headers=admin_headers,
        json={
            "action_code": "reboot-emg-host-01",
            "action_name": "重启应急主机01",
            "target_host_code": "emg-host-01",
            "module_type": "server",
            "action_category": "reboot_host",
            "system_id": system_id,
            "admin_user_id": 1,
            "script_type": "shell",
            "script_body": "sudo reboot",
            "enabled": True,
        },
    )
    assert action_resp.status_code == 200, action_resp.text

    mobile_actions = client.get("/api/v1/emergency/actions", headers=admin_headers)
    assert mobile_actions.status_code == 200, mobile_actions.text
    body = mobile_actions.json()
    assert body["server_actions"][0]["action_code"] == "reboot-emg-host-01"
    assert body["server_actions"][0]["host_ip"] == "10.0.0.10"
    assert "script_body" not in body["server_actions"][0]

    task_resp = client.post(
        "/api/v1/emergency/actions/execute",
        headers=admin_headers,
        json={"action_code": "reboot-emg-host-01"},
    )
    assert task_resp.status_code == 200, task_resp.text
    task = task_resp.json()
    assert task["task_id"] > 0
    assert task["status"] == "pending_approval"

    delete_action = client.delete(
        "/api/v1/admin/emergency-config/server-actions/reboot-emg-host-01",
        headers=admin_headers,
    )
    assert delete_action.status_code == 200, delete_action.text
    mobile_after_delete = client.get("/api/v1/emergency/actions", headers=admin_headers)
    assert mobile_after_delete.status_code == 200, mobile_after_delete.text
    assert mobile_after_delete.json()["server_actions"] == []

    delete_host = client.delete(
        "/api/v1/admin/emergency-config/ssh-hosts/emg-host-01",
        headers=admin_headers,
    )
    assert delete_host.status_code == 200, delete_host.text
    admin_config = client.get("/api/v1/admin/emergency-config", headers=admin_headers)
    assert admin_config.status_code == 200, admin_config.text
    assert admin_config.json()["ssh_hosts"] == []
