import app.db.session as db_session_module
from app.core.config import settings
from app.models.firewall import FirewallBlockConfig
from app.models.security_response import FeishuUserBinding, IpBlockBatch
from app.models.user import User


GATEWAY_TOKEN = "test_openclaw_gateway_token_32_chars"


def _headers(open_id="ou_allowed", channel="feishu", token=GATEWAY_TOKEN):
    return {
        "Authorization": f"Bearer {token}",
        "X-OpenClaw-Channel": channel,
        "X-Feishu-Open-Id": open_id,
    }


def _analysis(ip="2.2.2.2"):
    return {
        "summary": {"total": 1, "malicious": 1, "block_candidates": [ip]},
        "items": [
            {
                "resource_type": "ip",
                "ip": ip,
                "risk_level": "high_risk",
                "is_malicious": True,
                "should_block": True,
                "needs_manual_confirmation": False,
                "summary": "恶意且非济南",
            }
        ],
    }


def _configure_gateway(monkeypatch, permanent=False):
    monkeypatch.setattr(settings, "OPENCLAW_TOOL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(settings, "OPENCLAW_TOOL_GATEWAY_TOKEN", GATEWAY_TOKEN)
    monkeypatch.setattr(settings, "OPENCLAW_TOOL_ALLOWED_CLIENT_CIDRS", "")
    monkeypatch.setattr(settings, "OPENCLAW_TOOL_FIREWALL_TARGET_CODE", "test-primary")
    monkeypatch.setattr(settings, "OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK", permanent)


def _grant(open_id="ou_allowed", can_block=True):
    db = db_session_module.SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").one()
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
        db.add(
            FeishuUserBinding(
                open_id=open_id,
                display_name=open_id,
                aegis_user_id=user.id,
                can_query=True,
                can_block=can_block,
                enabled=True,
            )
        )
        db.commit()
    finally:
        db.close()


def _create_prepared_batch(client, monkeypatch, open_id="ou_allowed"):
    monkeypatch.setattr(
        "app.services.security_response.batch_query_ip_reputation",
        lambda *args, **kwargs: _analysis(),
    )
    response = client.post(
        "/aegis/tools/v1/ip/analyze",
        headers=_headers(open_id),
        json={"raw_input": "2.2.2.2", "session_key": "feishu:test"},
    )
    assert response.status_code == 200, response.text
    batch_id = response.json()["id"]
    response = client.post(
        f"/aegis/tools/v1/ip/batches/{batch_id}/prepare",
        headers=_headers(open_id),
        json={"selection": "recommended"},
    )
    assert response.status_code == 200, response.text
    return batch_id


def test_gateway_rejects_missing_trusted_context(client, monkeypatch):
    _configure_gateway(monkeypatch)
    _grant()

    assert client.get("/aegis/tools/v1/capabilities").status_code == 401
    assert client.get(
        "/aegis/tools/v1/capabilities",
        headers=_headers(channel="telegram"),
    ).status_code == 403
    assert client.get(
        "/aegis/tools/v1/capabilities",
        headers=_headers(token="wrong_token_that_is_still_long_enough"),
    ).status_code == 403


def test_gateway_enforces_feishu_whitelist(client, monkeypatch):
    _configure_gateway(monkeypatch)
    _grant("ou_query_only", can_block=False)

    assert client.get(
        "/aegis/tools/v1/capabilities",
        headers=_headers("ou_unknown"),
    ).status_code == 403
    db = db_session_module.SessionLocal()
    try:
        unknown = db.query(FeishuUserBinding).filter(FeishuUserBinding.open_id == "ou_unknown").one()
        assert unknown.enabled is False
        assert unknown.can_block is False
    finally:
        db.close()
    response = client.get(
        "/aegis/tools/v1/capabilities",
        headers=_headers("ou_query_only"),
    )
    assert response.status_code == 200
    assert response.json()["can_query"] is True
    assert response.json()["can_block"] is False

    monkeypatch.setattr(
        "app.services.security_response.batch_query_ip_reputation",
        lambda *args, **kwargs: _analysis(),
    )
    response = client.post(
        "/aegis/tools/v1/ip/analyze",
        headers=_headers("ou_query_only"),
        json={"raw_input": "2.2.2.2"},
    )
    assert response.status_code == 200
    batch_id = response.json()["id"]
    response = client.post(
        f"/aegis/tools/v1/ip/batches/{batch_id}/prepare",
        headers=_headers("ou_query_only"),
        json={"selection": "recommended"},
    )
    assert response.status_code == 403


def test_gateway_dry_run_and_batch_ownership(client, monkeypatch):
    _configure_gateway(monkeypatch)
    _grant("ou_allowed")
    _grant("ou_other")
    calls = []

    def fake_block(ips, reason, dry_run, db, target_code):
        calls.append((ips, dry_run, target_code))
        return {
            "status": "dry_run",
            "dry_run": dry_run,
            "ips": ips,
            "added_ips": [],
            "existing_ips": [],
            "verified_ips": [],
        }

    monkeypatch.setattr("app.services.security_response.block_ips_with_firewall", fake_block)
    batch_id = _create_prepared_batch(client, monkeypatch)

    response = client.get(
        f"/aegis/tools/v1/ip/batches/{batch_id}",
        headers=_headers("ou_other"),
    )
    assert response.status_code == 403

    response = client.post(
        f"/aegis/tools/v1/ip/batches/{batch_id}/execute",
        headers=_headers(),
        json={"dry_run": True, "confirmed": False},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "dry_run_succeeded"
    assert calls == [(["2.2.2.2"], True, "test-primary")]

    db = db_session_module.SessionLocal()
    try:
        batch = db.query(IpBlockBatch).filter(IpBlockBatch.id == batch_id).one()
        assert batch.source == "openclaw"
        assert batch.requester_open_id == "ou_allowed"
    finally:
        db.close()


def test_gateway_permanent_block_requires_switch_and_confirmation(client, monkeypatch):
    _configure_gateway(monkeypatch, permanent=False)
    _grant()
    monkeypatch.setattr(
        "app.services.security_response.block_ips_with_firewall",
        lambda ips, reason, dry_run, db, target_code: {
            "status": "success",
            "dry_run": dry_run,
            "ips": ips,
            "added_ips": ips,
            "existing_ips": [],
            "verified_ips": ips,
        },
    )
    batch_id = _create_prepared_batch(client, monkeypatch)
    endpoint = f"/aegis/tools/v1/ip/batches/{batch_id}/execute"

    response = client.post(
        endpoint,
        headers=_headers(),
        json={"dry_run": False, "confirmed": True},
    )
    assert response.status_code == 403

    monkeypatch.setattr(settings, "OPENCLAW_TOOL_ALLOW_PERMANENT_BLOCK", True)
    response = client.post(
        endpoint,
        headers=_headers(),
        json={"dry_run": False, "confirmed": False},
    )
    assert response.status_code == 400

    response = client.post(
        endpoint,
        headers=_headers(),
        json={"dry_run": False, "confirmed": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "succeeded"
