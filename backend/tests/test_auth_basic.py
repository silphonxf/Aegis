from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_failed_with_wrong_password():
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_success_and_me_with_token():
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    token = login.json().get("access_token")
    assert token

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json().get("username") == "admin"
