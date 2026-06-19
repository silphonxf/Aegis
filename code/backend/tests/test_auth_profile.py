def test_me_requires_valid_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_update_profile_and_change_password(client, admin_headers):
    profile = client.put(
        "/api/v1/auth/profile",
        headers=admin_headers,
        json={"nickname": "测试管理员", "avatar_url": "https://example.com/a.png"},
    )
    assert profile.status_code == 200, profile.text
    body = profile.json()
    assert body["nickname"] == "测试管理员"
    assert body["avatar_url"] == "https://example.com/a.png"

    change = client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"old_password": "test_admin_password_for_ci_only", "new_password": "changed_password_2026"},
    )
    assert change.status_code == 200, change.text

    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test_admin_password_for_ci_only"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changed_password_2026"},
    )
    assert new_login.status_code == 200, new_login.text
