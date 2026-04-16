from io import BytesIO

from openpyxl import Workbook


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
