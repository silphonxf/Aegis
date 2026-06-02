def test_get_emergency_config_empty(client, admin_headers):
    resp = client.get('/api/v1/admin/emergency-config', headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert 'ssh_hosts' in body
    assert 'server_actions' in body
    assert 'database_actions' in body
    assert 'process_actions' in body


def test_save_emergency_ssh_host(client, admin_headers, monkeypatch):
    monkeypatch.setenv('AEGIS_CREDENTIALS_MASTER_KEY', 'test-master-key')
    resp = client.post(
        '/api/v1/admin/emergency-config/ssh-hosts',
        headers=admin_headers,
        json={
            'host_code': 'foc-app-01',
            'host_name': '航信应用服务器-01',
            'host_ip': '10.10.1.21',
            'port': 22,
            'username': 'ops',
            'auth_type': 'password',
            'password_plaintext': 'secret-123',
            'connect_timeout_ms': 5000,
            'enabled': True,
            'remark': 'test',
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['host_code'] == 'foc-app-01'
    assert body['password_ciphertext'] == '***'


def test_save_emergency_server_action(client, admin_headers, monkeypatch):
    monkeypatch.setenv('AEGIS_CREDENTIALS_MASTER_KEY', 'test-master-key')
    client.post(
        '/api/v1/admin/emergency-config/ssh-hosts',
        headers=admin_headers,
        json={
            'host_code': 'foc-app-01',
            'host_name': '航信应用服务器-01',
            'host_ip': '10.10.1.21',
            'port': 22,
            'username': 'ops',
            'auth_type': 'password',
            'password_plaintext': 'secret-123',
            'connect_timeout_ms': 5000,
            'enabled': True,
            'remark': 'test',
        },
    )
    resp = client.post(
        '/api/v1/admin/emergency-config/server-actions',
        headers=admin_headers,
        json={
            'action_code': 'reboot-server',
            'action_name': '服务器重启',
            'target_host_code': 'foc-app-01',
            'module_type': 'server',
            'script_type': 'shell',
            'script_body': 'sudo reboot',
            'confirm_text': '确认重启？',
            'enabled': True,
            'remark': 'test',
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()['action_code'] == 'reboot-server'


def test_import_emergency_config_json(client, admin_headers):
    resp = client.post('/api/v1/admin/emergency-config/import-json', headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['ssh_hosts'] >= 1

    listing = client.get('/api/v1/admin/emergency-config', headers=admin_headers)
    assert listing.status_code == 200, listing.text
    config = listing.json()
    assert any(item['host_code'] == 'foc-app-01' for item in config['ssh_hosts'])
    assert any(item['action_code'] == 'reboot-server' for item in config['server_actions'])
