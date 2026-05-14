from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict

from fastapi import HTTPException

from app.schemas.emergency_config import (
    EmergencyDbActionItem,
    EmergencyOpsConfig,
    EmergencyProcessActionItem,
    EmergencyServerActionItem,
    EmergencySshHostItem,
    EmergencySshHostSaveRequest,
)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / 'config' / 'emergency_ops.json'


def _ensure_parent():
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    return '***'


def _encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    key = os.getenv('AEGIS_CREDENTIALS_MASTER_KEY') or os.getenv('AEGIS_SECRET_KEY')
    if not key:
        raise HTTPException(status_code=500, detail={'code': 'EMERGENCY_SECRET_KEY_MISSING', 'message': '未配置凭据主密钥环境变量'})
    payload = f'{key}:{value}'.encode('utf-8')
    return 'ENC:' + base64.b64encode(payload).decode('ascii')


def _public_host(item: EmergencySshHostItem) -> Dict:
    data = item.dict()
    data['password_ciphertext'] = _mask_secret(data.get('password_ciphertext'))
    data['private_key_ciphertext'] = _mask_secret(data.get('private_key_ciphertext'))
    data['private_key_passphrase_ciphertext'] = _mask_secret(data.get('private_key_passphrase_ciphertext'))
    return data


def load_emergency_config() -> EmergencyOpsConfig:
    if not _CONFIG_PATH.exists():
        return EmergencyOpsConfig()
    raw = json.loads(_CONFIG_PATH.read_text(encoding='utf-8'))
    return EmergencyOpsConfig(**raw)


def save_emergency_config(config: EmergencyOpsConfig) -> None:
    _ensure_parent()
    _CONFIG_PATH.write_text(json.dumps(config.dict(), ensure_ascii=False, indent=2), encoding='utf-8')


def list_public_config() -> Dict:
    config = load_emergency_config()
    return {
        'ssh_hosts': [_public_host(item) for item in config.ssh_hosts],
        'server_actions': [item.dict() for item in config.server_actions],
        'database_actions': [item.dict() for item in config.database_actions],
        'process_actions': [item.dict() for item in config.process_actions],
    }


def upsert_ssh_host(payload: EmergencySshHostSaveRequest) -> Dict:
    config = load_emergency_config()
    item = EmergencySshHostItem(
        host_code=payload.host_code,
        host_name=payload.host_name,
        host_ip=payload.host_ip,
        port=payload.port,
        username=payload.username,
        auth_type=payload.auth_type,
        password_ciphertext=_encrypt_secret(payload.password_plaintext) if payload.password_plaintext else payload.password_ciphertext,
        private_key_ciphertext=_encrypt_secret(payload.private_key_plaintext) if payload.private_key_plaintext else payload.private_key_ciphertext,
        private_key_passphrase_ciphertext=_encrypt_secret(payload.private_key_passphrase_plaintext) if payload.private_key_passphrase_plaintext else payload.private_key_passphrase_ciphertext,
        connect_timeout_ms=payload.connect_timeout_ms,
        enabled=payload.enabled,
        remark=payload.remark,
    )
    config.ssh_hosts = [x for x in config.ssh_hosts if x.host_code != item.host_code] + [item]
    save_emergency_config(config)
    return _public_host(item)


def upsert_server_action(payload: EmergencyServerActionItem) -> Dict:
    config = load_emergency_config()
    config.server_actions = [x for x in config.server_actions if x.action_code != payload.action_code] + [payload]
    save_emergency_config(config)
    return payload.dict()


def upsert_db_action(payload: EmergencyDbActionItem) -> Dict:
    config = load_emergency_config()
    config.database_actions = [x for x in config.database_actions if x.action_code != payload.action_code] + [payload]
    save_emergency_config(config)
    return payload.dict()


def upsert_process_action(payload: EmergencyProcessActionItem) -> Dict:
    config = load_emergency_config()
    config.process_actions = [x for x in config.process_actions if x.action_code != payload.action_code] + [payload]
    save_emergency_config(config)
    return payload.dict()
