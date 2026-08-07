import app.db.session as db_session_module
from app.models.security_response import FeishuUserBinding, IpBlockBatch
from app.models.firewall import FirewallBlockConfig
from app.models.user import User


def _analysis():
    return {
        "summary": {"total": 2, "malicious": 2, "block_candidates": ["2.2.2.2"]},
        "items": [
            {
                "resource_type": "ip",
                "ip": "1.1.1.1",
                "risk_level": "high_risk",
                "is_malicious": True,
                "should_block": False,
                "needs_manual_confirmation": True,
                "summary": "归属地为济南，需要二次确认",
            },
            {
                "resource_type": "ip",
                "ip": "2.2.2.2",
                "risk_level": "high_risk",
                "is_malicious": True,
                "should_block": True,
                "needs_manual_confirmation": False,
                "summary": "恶意且非济南",
            },
        ],
    }


def _grant_zhang(client, admin_headers):
    db = db_session_module.SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        user_id = user.id
        if not db.query(FirewallBlockConfig).filter(FirewallBlockConfig.target_code == "test-primary").first():
            db.add(
                FirewallBlockConfig(
                    target_code="test-primary",
                    target_name="山石测试设备",
                    is_default=True,
                    is_test_target=True,
                    enabled=True,
                    scheme="https",
                    firewall_ip="192.0.2.10",
                    port=443,
                    address_book_name="aegis-test-blocked-ip",
                    verify_ssl=False,
                    timeout_seconds=15,
                    addrbook_path="/api/addrbook",
                )
            )
            db.commit()
    finally:
        db.close()
    response = client.put(
        "/api/v1/admin/security-response/feishu-bindings",
        headers=admin_headers,
        json={
            "open_id": "ou_zhangxiaofan",
            "display_name": "张晓帆",
            "aegis_user_id": user_id,
            "can_query": True,
            "can_block": True,
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return user_id


def test_feishu_binding_requires_admin_for_block_permission(client, admin_headers):
    response = client.put(
        "/api/v1/admin/security-response/feishu-bindings",
        headers=admin_headers,
        json={
            "open_id": "ou_unmapped",
            "display_name": "未绑定用户",
            "aegis_user_id": None,
            "can_query": True,
            "can_block": True,
            "enabled": True,
        },
    )
    assert response.status_code == 400


def test_jinan_batch_requires_second_confirmation_then_dry_run(
    client,
    admin_headers,
    monkeypatch,
):
    _grant_zhang(client, admin_headers)
    monkeypatch.setattr(
        "app.services.security_response.batch_query_ip_reputation",
        lambda *args, **kwargs: _analysis(),
    )
    firewall_calls = []

    def fake_block(ips, reason, dry_run, db, target_code):
        firewall_calls.append((ips, dry_run, target_code))
        return {
            "status": "dry_run",
            "dry_run": True,
            "ips": ips,
            "added_ips": [],
            "existing_ips": [],
            "verified_ips": [],
        }

    monkeypatch.setattr("app.services.security_response.block_ips_with_firewall", fake_block)
    response = client.post(
        "/api/v1/admin/security-response/batches/analyze",
        headers=admin_headers,
        json={
            "raw_input": "1.1.1.1 2.2.2.2",
            "requester_open_id": "ou_zhangxiaofan",
            "firewall_target_code": "test-primary",
        },
    )
    assert response.status_code == 200, response.text
    batch_id = response.json()["id"]

    response = client.post(
        f"/api/v1/admin/security-response/batches/{batch_id}/prepare",
        headers=admin_headers,
        json={"selection": "all_malicious", "confirmer_open_id": "ou_zhangxiaofan"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "jinan_confirmation_pending"

    response = client.post(
        f"/api/v1/admin/security-response/batches/{batch_id}/execute",
        headers=admin_headers,
        json={"confirmer_open_id": "ou_zhangxiaofan", "dry_run": True},
    )
    assert response.status_code == 400
    assert firewall_calls == []

    response = client.post(
        f"/api/v1/admin/security-response/batches/{batch_id}/confirm-jinan",
        headers=admin_headers,
        json={"confirmer_open_id": "ou_zhangxiaofan"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["jinan_confirmed"] is True
    assert response.json()["status"] == "execution_confirmation_pending"

    response = client.post(
        f"/api/v1/admin/security-response/batches/{batch_id}/execute",
        headers=admin_headers,
        json={"confirmer_open_id": "ou_zhangxiaofan", "dry_run": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "dry_run_succeeded"
    assert firewall_calls == [(["1.1.1.1", "2.2.2.2"], True, "test-primary")]


def test_repeated_execution_is_rejected(client, admin_headers, monkeypatch):
    _grant_zhang(client, admin_headers)
    analysis = _analysis()
    analysis["items"] = [analysis["items"][1]]
    monkeypatch.setattr(
        "app.services.security_response.batch_query_ip_reputation",
        lambda *args, **kwargs: analysis,
    )
    monkeypatch.setattr(
        "app.services.security_response.block_ips_with_firewall",
        lambda ips, reason, dry_run, db, target_code: {
            "status": "dry_run",
            "ips": ips,
            "added_ips": [],
            "existing_ips": [],
            "verified_ips": [],
        },
    )
    response = client.post(
        "/api/v1/admin/security-response/batches/analyze",
        headers=admin_headers,
        json={"raw_input": "2.2.2.2", "requester_open_id": "ou_zhangxiaofan"},
    )
    batch_id = response.json()["id"]
    response = client.post(
        f"/api/v1/admin/security-response/batches/{batch_id}/prepare",
        headers=admin_headers,
        json={"selection": "recommended", "confirmer_open_id": "ou_zhangxiaofan"},
    )
    assert response.json()["status"] == "execution_confirmation_pending"
    endpoint = f"/api/v1/admin/security-response/batches/{batch_id}/execute"
    payload = {"confirmer_open_id": "ou_zhangxiaofan", "dry_run": True}
    assert client.post(endpoint, headers=admin_headers, json=payload).status_code == 200
    assert client.post(endpoint, headers=admin_headers, json=payload).status_code == 400

    db = db_session_module.SessionLocal()
    try:
        assert db.query(IpBlockBatch).filter(IpBlockBatch.id == batch_id).one().status == "dry_run_succeeded"
        assert db.query(FeishuUserBinding).filter(FeishuUserBinding.open_id == "ou_zhangxiaofan").count() == 1
    finally:
        db.close()
