def test_toolbox_ping_and_port_check(client, admin_headers):
    ping = client.post(
        "/api/v1/toolbox/ping",
        headers=admin_headers,
        json={"host": "127.0.0.1", "count": 1},
    )
    assert ping.status_code == 200, ping.text
    assert ping.json()["host"] == "127.0.0.1"

    port = client.post(
        "/api/v1/toolbox/port-check",
        headers=admin_headers,
        json={"host": "127.0.0.1", "port": 65535, "timeout_ms": 100},
    )
    assert port.status_code == 200, port.text
    assert port.json()["port"] == 65535


def test_toolbox_restart_task_status_flow(client, admin_headers):
    create = client.post(
        "/api/v1/toolbox/restart-task",
        headers=admin_headers,
        json={"target": "local-host", "reason": "pytest"},
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["id"]

    approve = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "approved", "note": "ok"},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"

    running = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "running", "note": "started", "executor": "manual"},
    )
    assert running.status_code == 200, running.text
    assert running.json()["status"] == "running"

    done = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "done", "note": "finished", "executor": "manual"},
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "done"
    assert done.json()["result"]["success"] is True


def test_toolbox_invalid_status_transition(client, admin_headers):
    create = client.post(
        "/api/v1/toolbox/restart-task",
        headers=admin_headers,
        json={"target": "local-host", "reason": "pytest-invalid"},
    )
    task_id = create.json()["id"]

    invalid = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "done", "note": "skip approval"},
    )
    assert invalid.status_code == 400, invalid.text
    assert invalid.json()["code"] == "TASK_STATUS_INVALID"

    approve = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "approved", "note": "ok"},
    )
    assert approve.status_code == 200, approve.text

    invalid2 = client.put(
        f"/api/v1/toolbox/tasks/{task_id}/status",
        headers=admin_headers,
        json={"status": "rejected", "note": "cannot reject after approve"},
    )
    assert invalid2.status_code == 400, invalid2.text
    assert invalid2.json()["code"] == "TASK_STATUS_INVALID"
