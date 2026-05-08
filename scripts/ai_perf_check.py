#!/usr/bin/env python3
import json
import ssl
import sys
import time
import urllib.request

BASE = 'https://127.0.0.1:8000'
CTX = ssl._create_unverified_context()
USERNAME = 'admin'
PASSWORD = 'local_admin_pass_2026'


def req(path, method='GET', data=None, token=None, timeout=20):
    body = json.dumps(data).encode() if data is not None else None
    headers = {'Content-Type': 'application/json'} if body is not None else {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    started = time.time()
    with urllib.request.urlopen(request, context=CTX, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    return round(time.time() - started, 3), payload


def main():
    _, login = req('/api/v1/auth/login', 'POST', {'username': USERNAME, 'password': PASSWORD}, timeout=10)
    token = login['access_token']

    list_elapsed, conversations = req('/api/v1/ai/conversations', 'GET', token=token, timeout=10)
    print(json.dumps({'kind': 'conversations_list', 'elapsed_s': list_elapsed, 'total': conversations.get('total', 0)}, ensure_ascii=False))

    _, conv = req('/api/v1/ai/conversations', 'POST', {'title': 'AI性能检测会话', 'source': 'mobile'}, token=token, timeout=10)
    conversation_id = conv['conversation_id']

    detail_elapsed, detail = req(f'/api/v1/ai/conversations/{conversation_id}', 'GET', token=token, timeout=10)
    print(json.dumps({'kind': 'conversation_detail', 'elapsed_s': detail_elapsed, 'conversation_id': conversation_id, 'message_count': detail.get('message_count', 0), 'attachment_count': detail.get('attachment_count', 0)}, ensure_ascii=False))

    chat_elapsed, chat = req('/api/v1/ai/chat/v2', 'POST', {
        'conversation_id': conversation_id,
        'message': '请只回复“性能测试正常”四个字。',
        'attachments': [],
    }, token=token, timeout=60)
    print(json.dumps({'kind': 'chat_v2', 'elapsed_s': chat_elapsed, 'mode': chat.get('mode'), 'reply': chat.get('reply'), 'fallback_reason': chat.get('fallback_reason')}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(json.dumps({'kind': 'error', 'message': str(e)}, ensure_ascii=False))
        sys.exit(1)
