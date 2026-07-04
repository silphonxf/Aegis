from io import BytesIO

from openpyxl import Workbook

from app.services import threatbook
from app.core.config import settings


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
    assert body["request"]["body"][0]["name"] == "aegis-blocked-ip"
    assert body["request"]["body"][0]["member"] == ["8.8.8.8/32"]


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
                "result": [{"name": "aegis-blocked-ip", "member": ["1.1.1.1/32"], "is_ipv6": "0", "is_ordered": "0"}],
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
    put_body = calls[2][2]["data"]
    assert '"name": "aegis-blocked-ip"' in put_body
    assert '"member": ["1.1.1.1/32", "9.9.9.9/32"]' in put_body
    assert calls[2][2]["cookies"]["token"] == "tok"


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
