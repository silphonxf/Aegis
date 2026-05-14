import base64


def test_ai_conversation_restore_flow(client, admin_headers):
    created = client.post(
        "/api/v1/ai/conversations",
        headers=admin_headers,
        json={"title": "新会话", "source": "mobile"},
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    payload = "trace_id=abc123\nerror=timeout while calling upstream service"
    data_url = "data:text/plain;base64," + base64.b64encode(payload.encode("utf-8")).decode("ascii")
    uploaded = client.post(
        "/api/v1/ai/files/upload",
        headers=admin_headers,
        json={
            "conversation_id": conversation_id,
            "name": "gateway-timeout.log",
            "type": "text/plain",
            "size": len(payload.encode("utf-8")),
            "data_url": data_url,
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    uploaded_file = uploaded.json()["file"]
    assert uploaded_file["preview_excerpt"].startswith("trace_id=abc123")

    replied = client.post(
        "/api/v1/ai/chat/v2",
        headers=admin_headers,
        json={
            "conversation_id": conversation_id,
            "message": "请结合附件判断超时原因",
            "attachments": [
                {
                    "file_id": uploaded_file["file_id"],
                    "name": uploaded_file["name"],
                    "type": uploaded_file["type"],
                    "size": uploaded_file["size"],
                }
            ],
        },
    )
    assert replied.status_code == 200, replied.text
    chat_body = replied.json()
    assert chat_body["conversation_id"] == conversation_id
    assert chat_body["reply"]
    assert chat_body["mode"] in {"rule_fallback", "openclaw"}

    detail = client.get(f"/api/v1/ai/conversations/{conversation_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["conversation_id"] == conversation_id
    assert detail_body["message_count"] == 2
    assert detail_body["attachment_count"] == 1
    assert detail_body["title"] == "请结合附件判断超时原因"
    assert [item["role"] for item in detail_body["messages"]] == ["user", "assistant"]
    assert detail_body["messages"][0]["content"] == "请结合附件判断超时原因"
    assert detail_body["attachments"][0]["name"] == "gateway-timeout.log"

    listed = client.get("/api/v1/ai/conversations", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert any(item["conversation_id"] == conversation_id for item in items)


def test_ai_conversation_rename(client, admin_headers):
    created = client.post(
        "/api/v1/ai/conversations",
        headers=admin_headers,
        json={"title": "新会话", "source": "mobile"},
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    renamed = client.put(
        f"/api/v1/ai/conversations/{conversation_id}",
        headers=admin_headers,
        json={"title": "网络超时排查"},
    )
    assert renamed.status_code == 200, renamed.text
    body = renamed.json()
    assert body["conversation_id"] == conversation_id
    assert body["title"] == "网络超时排查"
