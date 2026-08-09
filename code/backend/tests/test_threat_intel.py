import json
from io import BytesIO

from openpyxl import Workbook

from app.services import threatbook
from app.core.config import settings
import app.db.session as db_session_module
from app.models.firewall import FirewallBlockConfig
from app.services.firewall import HillstoneRestClient


def test_normalize_ip_list_accepts_mixed_separators_and_deduplicates():
    assert threatbook.normalize_ip_list([
        "1.1.1.1 2.2.2.2，3.3.3.3; 1.1.1.1\n4.4.4.4",
    ]) == ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]


def test_threat_intel_quick_query_rule_jinan_confirm(client, admin_headers, monkeypatch):
    def fake_batch_query_ip_reputation(raw_items, lang="zh", realtime_verdict=True):
        return {
            "query": {"ips": ["1.1.1.1", "2.2.2.2"], "count": 2, "lang": lang, "realtime_verdict": realtime_verdict},
            "summary": {"total": 2, "malicious": 2, "high_risk": 1, "block_candidates": ["2.2.2.2"]},
            "items": [
                {
                    "ip": "1.1.1.1",
                    "is_malicious": True,
                    "risk_level": "high_risk",
                    "should_block": False,
                    "needs_manual_confirmation": True,
                    "decision": "confirm_then_block",
                    "summary": "归属地为济南，高危时需二次确认后再封禁",
                },
                {
                    "ip": "2.2.2.2",
                    "is_malicious": True,
                    "risk_level": "high_risk",
                    "should_block": True,
                    "needs_manual_confirmation": False,
                    "decision": "block",
                    "summary": "is_malicious=true 且归属地非济南，满足自动封禁条件",
                },
            ],
            "response_code": 0,
            "verbose_msg": "成功",
        }

    monkeypatch.setattr("app.api.admin.batch_query_ip_reputation", fake_batch_query_ip_reputation)

    resp = client.post(
        "/api/v1/admin/threat-intel/ip-reputation/quick",
        headers=admin_headers,
        json={"raw_input": "1.1.1.1\n2.2.2.2", "lang": "zh", "realtime_verdict": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"][0]["needs_manual_confirmation"] is True
    assert body["items"][0]["decision"] == "confirm_then_block"
    assert body["items"][1]["should_block"] is True
    assert body["items"][1]["decision"] == "block"


def test_threatbook_unified_ip_and_domain_analysis(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def fake_get(url, params, timeout):
        calls.append((url, params["resource"]))
        if url.endswith("/scene/ip_reputation"):
            return FakeResponse({
                "response_code": 0,
                "verbose_msg": "OK",
                "data": {
                    "8.8.8.8": {
                        "basic": {"carrier": "Google", "location": {"country": "美国", "city": ""}},
                        "scene": "云服务商",
                        "judgments": ["Scanner"],
                        "intelligences": {},
                        "asn": {"rank": 2},
                    }
                },
            })
        return FakeResponse({
            "response_code": 0,
            "verbose_msg": "OK",
            "data": {
                "evil.example": {
                    "judgments": ["Phishing"],
                    "intelligences": {},
                    "categories": [{"first_cats": ["恶意网站"], "second_cats": "钓鱼"}],
                    "cur_ips": [{"ip": "1.2.3.4", "location": {"country": "德国"}}],
                }
            },
        })

    monkeypatch.setattr(settings, "THREATBOOK_API_KEY", "test-key")
    monkeypatch.setattr("app.services.threatbook.requests.get", fake_get)
    result = threatbook.batch_query_indicators(["8.8.8.8\nevil.example"], lang="zh")

    assert calls[0][0] == "https://api.threatbook.cn/v3/scene/ip_reputation"
    assert calls[1][0] == "https://api.threatbook.cn/v3/domain/query"
    assert result["items"][0]["ip_type"] == "云服务商"
    assert result["items"][0]["country"] == "美国"
    assert result["items"][0]["malicious_types"] == ["Scanner"]
    assert result["items"][1]["domain_type"] == "恶意网站、钓鱼"
    assert result["items"][1]["country"] == "德国"
    assert result["items"][1]["malicious_types"] == ["Phishing"]
    assert result["items"][1]["should_block"] is False


def test_threat_intel_excel_import(client, admin_headers, monkeypatch):
    def fake_batch_query_ip_reputation(raw_items, lang="zh", realtime_verdict=True):
        assert "10.0.0.1" in raw_items
        assert "10.0.0.2" in raw_items
        return {
            "query": {"ips": ["10.0.0.1", "10.0.0.2"], "count": 2, "lang": lang, "realtime_verdict": realtime_verdict},
            "summary": {"total": 2, "malicious": 1, "high_risk": 1, "block_candidates": ["10.0.0.2"]},
            "items": [],
            "response_code": 0,
            "verbose_msg": "成功",
        }

    monkeypatch.setattr("app.api.admin.batch_query_ip_reputation", fake_batch_query_ip_reputation)

    wb = Workbook()
    ws = wb.active
    ws.append(["IP地址", "备注"])
    ws.append(["10.0.0.1", "A"])
    ws.append(["10.0.0.2", "B"])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    resp = client.post(
        "/api/v1/admin/threat-intel/ip-reputation/excel?lang=zh&realtime_verdict=true",
        headers=admin_headers,
        files={"file": ("ips.xlsx", bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["import"]["filename"] == "ips.xlsx"
    assert body["summary"]["high_risk"] == 1


def test_threat_intel_block_ip_dry_run_returns_firewall_plan(client, admin_headers):
    settings.HILLSTONE_HOST = "192.168.100.18"

    resp = client.post(
        "/api/v1/admin/threat-intel/block-ip",
        headers=admin_headers,
        json={"ip": "8.8.8.8", "risk_level": "high_risk", "reason": "unit test", "dry_run": True},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "dry_run"
    assert body["dry_run"] is True
    assert body["vendor"] == "hillstone"
    assert body["ip"] == "8.8.8.8"
    assert body["firewall_host"] == "192.168.100.18"
    assert body["request"]["url"].endswith("/rest/api/addrbook")
    assert body["request"]["body"]["name"] == "aegis-blocked-ip"
    assert body["request"]["body"]["ip"] == [{"ip_addr": "8.8.8.8", "netmask": 32, "flag": 0}]


def test_threat_intel_block_ip_requires_firewall_credentials(client, admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "HILLSTONE_USERNAME", None)
    monkeypatch.setattr(settings, "HILLSTONE_PASSWORD", None)

    resp = client.post(
        "/api/v1/admin/threat-intel/block-ip",
        headers=admin_headers,
        json={"ip": "8.8.4.4", "dry_run": False},
    )

    assert resp.status_code == 503, resp.text
    assert resp.json()["code"] == "FIREWALL_CONFIG_MISSING"
    assert "HILLSTONE_USERNAME" in resp.json()["message"]


def test_threat_intel_block_ip_calls_hillstone_addrbook(client, admin_headers, monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, status_code=200, body=None):
            self.status_code = status_code
            self._body = body if body is not None else {"success": True, "result": []}
            self.text = str(self._body)

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return FakeResponse(
            body={
                "success": True,
                "result": [{"token": "tok", "role": "admin", "vsysId": "0", "fromrootvsys": "1"}],
            }
        )

    def fake_get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return FakeResponse(
            body={
                "success": True,
                "result": [
                    {
                        "is_ipv6": 0,
                        "type": 0,
                        "name": "aegis-blocked-ip",
                        "description": "",
                        "entry": [],
                        "ip": [{"ip_addr": "1.1.1.1", "netmask": 32, "flag": 0}],
                        "range": [],
                        "host": [],
                        "wildcard": [],
                        "country": [],
                    }
                ],
            }
        )

    def fake_put(url, **kwargs):
        calls.append(("PUT", url, kwargs))
        return FakeResponse(status_code=200, body={"success": True})

    monkeypatch.setattr(settings, "HILLSTONE_USERNAME", "admin")
    monkeypatch.setattr(settings, "HILLSTONE_PASSWORD", "secret")
    monkeypatch.setattr(settings, "HILLSTONE_HOST", "192.168.100.18")
    monkeypatch.setattr("app.services.firewall.requests.post", fake_post)
    monkeypatch.setattr("app.services.firewall.requests.get", fake_get)
    monkeypatch.setattr("app.services.firewall.requests.put", fake_put)

    resp = client.post(
        "/api/v1/admin/threat-intel/block-ip",
        headers=admin_headers,
        json={"ip": "9.9.9.9", "reason": "risk & block", "dry_run": False},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "blocked"
    assert body["vendor"] == "hillstone"
    assert body["http_status"] == 200
    assert body["method"] == "PUT"
    assert [call[0] for call in calls] == ["POST", "GET", "PUT"]
    assert calls[0][1].endswith("/rest/api/login")
    assert calls[1][1].startswith("https://192.168.100.18:443/rest/api/addrbook?query=")
    assert calls[2][1].endswith("/rest/api/addrbook")
    put_body = json.loads(calls[2][2]["data"])
    assert put_body["name"] == "aegis-blocked-ip"
    assert put_body["ip"] == [
        {"ip_addr": "1.1.1.1", "netmask": 32, "flag": 0},
        {"ip_addr": "9.9.9.9", "netmask": 32, "flag": 0},
    ]
    assert calls[2][2]["cookies"]["token"] == "tok"


def test_hillstone_addrbook_payload_converts_legacy_member(monkeypatch):
    monkeypatch.setattr(settings, "HILLSTONE_ADDRESS_BOOK_NAME", "xdr_soar_in_v4")
    client = HillstoneRestClient()

    payload = client.build_addrbook_payload(
        "1.2.3.4",
        None,
        {
            "name": "xdr_soar_in_v4",
            "member": ["216.250.248.88/32", "16.163.96.158/32"],
        },
    )

    assert payload == {
        "is_ipv6": 0,
        "type": 0,
        "name": "xdr_soar_in_v4",
        "description": "",
        "entry": [],
        "ip": [
            {"ip_addr": "216.250.248.88", "netmask": 32, "flag": 0},
            {"ip_addr": "16.163.96.158", "netmask": 32, "flag": 0},
            {"ip_addr": "1.2.3.4", "netmask": 32, "flag": 0},
        ],
        "range": [],
        "host": [],
        "wildcard": [],
        "country": [],
    }


def test_hillstone_batch_block_updates_once_and_verifies(monkeypatch):
    calls = []
    get_count = 0

    class FakeResponse:
        status_code = 200
        text = '{"success": true}'

        def __init__(self, body):
            self._body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

    def addrbook(ips):
        return {
            "success": True,
            "result": [
                {
                    "name": "aegis-blocked-ip",
                    "ip": [{"ip_addr": ip, "netmask": 32, "flag": 0} for ip in ips],
                }
            ],
        }

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return FakeResponse({"success": True, "result": [{"token": "tok"}]})

    def fake_get(url, **kwargs):
        nonlocal get_count
        get_count += 1
        calls.append(("GET", url, kwargs))
        return FakeResponse(addrbook(["1.1.1.1"] if get_count == 1 else ["1.1.1.1", "2.2.2.2", "3.3.3.3"]))

    def fake_put(url, **kwargs):
        calls.append(("PUT", url, kwargs))
        return FakeResponse({"success": True})

    monkeypatch.setattr(settings, "HILLSTONE_USERNAME", "admin")
    monkeypatch.setattr(settings, "HILLSTONE_PASSWORD", "secret")
    monkeypatch.setattr("app.services.firewall.requests.post", fake_post)
    monkeypatch.setattr("app.services.firewall.requests.get", fake_get)
    monkeypatch.setattr("app.services.firewall.requests.put", fake_put)

    result = HillstoneRestClient().block_ips(
        ["1.1.1.1", "2.2.2.2", "3.3.3.3", "2.2.2.2"],
        reason="batch test",
        dry_run=False,
    )

    assert [method for method, _, _ in calls] == ["POST", "GET", "PUT", "GET"]
    assert result["existing_ips"] == ["1.1.1.1"]
    assert result["added_ips"] == ["2.2.2.2", "3.3.3.3"]
    assert result["verified_ips"] == ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
    put_body = json.loads(calls[2][2]["data"])
    assert [item["ip_addr"] for item in put_body["ip"]] == ["1.1.1.1", "2.2.2.2", "3.3.3.3"]


def test_threat_intel_firewall_config_encrypts_credentials(client, admin_headers):
    resp = client.put(
        "/api/v1/admin/threat-intel/firewall-config",
        headers=admin_headers,
        json={
            "enabled": True,
            "scheme": "https",
            "firewall_ip": "10.67.82.6",
            "port": 443,
            "address_book_name": "xdr_soar_in_v4",
            "username": "fengjin",
            "password": "secret-password",
            "verify_ssl": False,
            "timeout_seconds": 15,
            "addrbook_path": "/api/addrbook",
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["firewall_ip"] == "10.67.82.6"
    assert body["address_book_name"] == "xdr_soar_in_v4"
    assert body["has_username"] is True
    assert body["has_password"] is True
    assert "username" not in body
    assert "password" not in body

    db = db_session_module.SessionLocal()
    try:
        row = db.query(FirewallBlockConfig).first()
        assert row is not None
        assert row.username_encrypted != "fengjin"
        assert row.password_encrypted != "secret-password"
    finally:
        db.close()

    resp = client.get("/api/v1/admin/threat-intel/firewall-config", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "database"
    assert body["has_username"] is True
    assert body["has_password"] is True
    assert "username" not in body
    assert "password" not in body


def test_threat_intel_block_ip_uses_database_firewall_config(client, admin_headers, monkeypatch):
    calls = []

    config_resp = client.put(
        "/api/v1/admin/threat-intel/firewall-config",
        headers=admin_headers,
        json={
            "enabled": True,
            "scheme": "https",
            "firewall_ip": "10.67.82.6",
            "port": 443,
            "address_book_name": "xdr_soar_in_v4",
            "username": "db-user",
            "password": "db-pass",
            "verify_ssl": False,
            "timeout_seconds": 15,
            "addrbook_path": "/api/addrbook",
        },
    )
    assert config_resp.status_code == 200, config_resp.text

    class FakeResponse:
        def __init__(self, status_code=200, body=None):
            self.status_code = status_code
            self._body = body if body is not None else {"success": True, "result": []}
            self.text = str(self._body)

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        assert json.loads(kwargs["data"])["userName"] != "db-user"
        return FakeResponse(body={"success": True, "result": [{"token": "tok", "role": "admin", "vsysId": "0", "fromrootvsys": "1"}]})

    def fake_get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return FakeResponse(
            body={
                "success": True,
                "result": [
                    {
                        "is_ipv6": 0,
                        "type": 0,
                        "name": "xdr_soar_in_v4",
                        "description": "",
                        "entry": [],
                        "ip": [{"ip_addr": "216.250.248.88", "netmask": 32, "flag": 0}],
                        "range": [],
                        "host": [],
                        "wildcard": [],
                        "country": [],
                    }
                ],
            }
        )

    def fake_put(url, **kwargs):
        calls.append(("PUT", url, kwargs))
        return FakeResponse(status_code=200, body={"success": True})

    monkeypatch.setattr("app.services.firewall.requests.post", fake_post)
    monkeypatch.setattr("app.services.firewall.requests.get", fake_get)
    monkeypatch.setattr("app.services.firewall.requests.put", fake_put)

    resp = client.post(
        "/api/v1/admin/threat-intel/block-ip",
        headers=admin_headers,
        json={"ip": "1.2.3.4", "reason": "db config", "dry_run": False},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["firewall_host"] == "10.67.82.6"
    assert body["address_set"] == "xdr_soar_in_v4"
    assert [call[0] for call in calls] == ["POST", "GET", "PUT"]
    put_body = json.loads(calls[2][2]["data"])
    assert put_body["ip"] == [
        {"ip_addr": "216.250.248.88", "netmask": 32, "flag": 0},
        {"ip_addr": "1.2.3.4", "netmask": 32, "flag": 0},
    ]


def test_threatbook_ip_key_response_and_scanner_judgment_are_malicious(monkeypatch):
    def fake_fetch_ip_reputation(ips, lang="zh", realtime_verdict=True):
        assert ips == ["66.240.205.34"]
        return {
            "response_code": 0,
            "verbose_msg": "成功",
            "data": {
                "66.240.205.34": {
                    "is_malicious": False,
                    "judgments": ["Scanner"],
                    "severity": "high",
                    "confidence_level": "high",
                    "basic": {
                        "location": {
                            "country": "United States",
                            "province": "California",
                            "city": "San Jose",
                        }
                    },
                }
            },
        }

    monkeypatch.setattr(threatbook, "fetch_ip_reputation", fake_fetch_ip_reputation)

    result = threatbook.batch_query_ip_reputation(["66.240.205.34"])

    item = result["items"][0]
    assert item["is_malicious"] is True
    assert item["risk_level"] == "high_risk"
    assert item["should_block"] is True
    assert item["decision"] == "block"
    assert item["malicious_judgments"] == ["Scanner"]
    assert result["summary"]["malicious"] == 1
    assert result["summary"]["high_risk"] == 1
    assert result["summary"]["block_candidates"] == ["66.240.205.34"]


def test_threatbook_ip_reputation_batches_resources_and_realtime_verdict(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response_code": 0,
                "verbose_msg": "Ok",
                "data": {
                    "1.1.1.1": {"is_malicious": False, "judgments": ["Info"]},
                    "2.2.2.2": {"is_malicious": True, "judgments": ["Scanner"]},
                },
            }

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return FakeResponse()

    monkeypatch.setattr(settings, "THREATBOOK_API_KEY", "test-key")
    monkeypatch.setattr("app.services.threatbook.requests.get", fake_get)

    result = threatbook.batch_query_ip_reputation(
        ["1.1.1.1", "2.2.2.2"],
        realtime_verdict=False,
    )

    assert len(calls) == 1
    assert calls[0][0] == "https://api.threatbook.cn/v3/scene/ip_reputation"
    assert calls[0][1]["resource"] == "1.1.1.1,2.2.2.2"
    assert calls[0][1]["realtime_verdict"] == "false"
    assert result["items"][0]["is_malicious"] is False
    assert result["items"][1]["malicious_judgments"] == ["Scanner"]


def test_ip_block_template_and_excel_import_without_threatbook(client, admin_headers):
    template = client.get(
        "/api/v1/admin/threat-intel/ip-block-template",
        headers=admin_headers,
    )
    assert template.status_code == 200
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["IP地址", "封禁原因", "备注"])
    sheet.append(["1.1.1.1", "扫描源", "第一条"])
    sheet.append(["not-an-ip", "无效", "应被跳过"])
    sheet.append(["2.2.2.2", "暴力破解", None])
    content = BytesIO()
    workbook.save(content)
    content.seek(0)

    response = client.post(
        "/api/v1/admin/threat-intel/ip-block-import",
        headers=admin_headers,
        data={"verify_with_threatbook": "false", "realtime_verdict": "true"},
        files={"file": ("block-list.xlsx", content.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == {"valid": 2, "invalid": 1, "malicious": 0, "block_candidates": []}
    assert body["items"][0]["ip"] == "1.1.1.1"
    assert body["items"][0]["import_reason"] == "扫描源"
    assert body["items"][0]["risk_level"] == "unverified"
    assert body["invalid_rows"][0]["ip"] == "not-an-ip"


def test_threat_intel_batch_block_uses_verified_firewall_flow(client, admin_headers, monkeypatch):
    calls = []

    def fake_block(ips, reason, dry_run, db, target_code):
        calls.append((ips, reason, dry_run, target_code))
        return {
            "status": "blocked",
            "dry_run": False,
            "ips": ips,
            "added_ips": ips,
            "existing_ips": [],
            "verified_ips": ips,
        }

    monkeypatch.setattr("app.api.admin.block_ips_with_firewall", fake_block)
    response = client.post(
        "/api/v1/admin/threat-intel/block-ips",
        headers=admin_headers,
        json={
            "ips": ["1.1.1.1", "2.2.2.2", "1.1.1.1"],
            "reason": "页面批量封禁",
            "dry_run": False,
            "source": "ip-block-console",
        },
    )

    assert response.status_code == 200, response.text
    assert calls == [(["1.1.1.1", "2.2.2.2"], "页面批量封禁", False, None)]
    assert response.json()["verified_ips"] == ["1.1.1.1", "2.2.2.2"]
