def test_login_failed_with_wrong_password(client):
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "AUTH_INVALID"


def test_login_success_and_me_with_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test_admin_password_for_ci_only"},
    )
    assert login.status_code == 200
    token = login.json().get("access_token")
    assert token

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json().get("username") == "admin"
    assert me.json().get("role") == "super_admin"
