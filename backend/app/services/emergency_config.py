from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.shared_data import EmergencyHost, Runbook
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


def _load_json_config() -> EmergencyOpsConfig:
    if not _CONFIG_PATH.exists():
        return EmergencyOpsConfig()
    raw = json.loads(_CONFIG_PATH.read_text(encoding='utf-8'))
    return EmergencyOpsConfig(**raw)


def save_emergency_config(config: EmergencyOpsConfig) -> None:
    _ensure_parent()
    _CONFIG_PATH.write_text(json.dumps(config.dict(), ensure_ascii=False, indent=2), encoding='utf-8')


def _db_has_emergency_data(db: Session) -> bool:
    return bool(db.query(EmergencyHost.id).first() or db.query(Runbook.id).first())


def _host_from_model(item: EmergencyHost) -> EmergencySshHostItem:
    return EmergencySshHostItem(
        host_code=item.host_code,
        host_name=item.host_name,
        host_ip=item.host_ip,
        port=item.port,
        username=item.username,
        auth_type=item.auth_type,
        password_ciphertext=item.password_ciphertext,
        private_key_ciphertext=item.private_key_ciphertext,
        private_key_passphrase_ciphertext=item.private_key_passphrase_ciphertext,
        connect_timeout_ms=item.connect_timeout_ms,
        enabled=item.is_active,
        remark=item.remark,
    )


def _server_action_from_runbook(item: Runbook, host_code: str) -> EmergencyServerActionItem:
    return EmergencyServerActionItem(
        action_code=item.runbook_code,
        action_name=item.runbook_name,
        target_host_code=host_code,
        module_type='server',
        script_type=item.script_type,
        script_body=item.script_body,
        confirm_text=item.confirm_text,
        enabled=item.enabled,
        remark=item.remark,
    )


def _db_action_from_runbook(item: Runbook, host_code: Optional[str]) -> EmergencyDbActionItem:
    return EmergencyDbActionItem(
        action_code=item.runbook_code,
        action_name=item.runbook_name,
        module_type='database',
        db_type='mysql',
        target_host_code=host_code,
        script_type=item.script_type,
        script_body=item.script_body,
        enabled=item.enabled,
        remark=item.remark,
    )


def _process_action_from_runbook(item: Runbook, host_code: str) -> EmergencyProcessActionItem:
    return EmergencyProcessActionItem(
        action_code=item.runbook_code,
        action_name=item.runbook_name,
        module_type='process',
        target_host_code=host_code,
        process_name=item.runbook_name,
        process_id_source='runtime_detect',
        script_type=item.script_type,
        script_body=item.script_body,
        enabled=item.enabled,
        remark=item.remark,
    )


def _load_db_config(db: Session) -> EmergencyOpsConfig:
    hosts = db.query(EmergencyHost).order_by(EmergencyHost.id.asc()).all()
    host_map = {item.id: item for item in hosts}
    runbooks = db.query(Runbook).order_by(Runbook.id.asc()).all()

    server_actions: List[EmergencyServerActionItem] = []
    database_actions: List[EmergencyDbActionItem] = []
    process_actions: List[EmergencyProcessActionItem] = []

    for rb in runbooks:
        host = host_map.get(rb.target_host_id) if rb.target_host_id else None
        host_code = host.host_code if host else ''
        if rb.runbook_type == 'server' and host_code:
            server_actions.append(_server_action_from_runbook(rb, host_code))
        elif rb.runbook_type == 'database':
            database_actions.append(_db_action_from_runbook(rb, host_code or None))
        elif rb.runbook_type == 'process' and host_code:
            process_actions.append(_process_action_from_runbook(rb, host_code))

    return EmergencyOpsConfig(
        ssh_hosts=[_host_from_model(item) for item in hosts],
        server_actions=server_actions,
        database_actions=database_actions,
        process_actions=process_actions,
    )


def load_emergency_config(db: Optional[Session] = None) -> EmergencyOpsConfig:
    if db is not None and _db_has_emergency_data(db):
        return _load_db_config(db)
    return _load_json_config()


def list_public_config(db: Optional[Session] = None) -> Dict:
    config = load_emergency_config(db)
    return {
        'ssh_hosts': [_public_host(item) for item in config.ssh_hosts],
        'server_actions': [item.dict() for item in config.server_actions],
        'database_actions': [item.dict() for item in config.database_actions],
        'process_actions': [item.dict() for item in config.process_actions],
    }


def _resolve_host_id(db: Session, host_code: Optional[str]) -> Optional[int]:
    if not host_code:
        return None
    host = db.query(EmergencyHost).filter(EmergencyHost.host_code == host_code).first()
    return host.id if host else None


def upsert_ssh_host(payload: EmergencySshHostSaveRequest, db: Optional[Session] = None) -> Dict:
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
    if db is None:
        config = _load_json_config()
        config.ssh_hosts = [x for x in config.ssh_hosts if x.host_code != item.host_code] + [item]
        save_emergency_config(config)
        return _public_host(item)

    host = db.query(EmergencyHost).filter(EmergencyHost.host_code == item.host_code).first()
    if not host:
        host = EmergencyHost(host_code=item.host_code)
        db.add(host)
    host.host_name = item.host_name
    host.host_ip = item.host_ip
    host.port = item.port
    host.username = item.username
    host.auth_type = item.auth_type
    host.password_ciphertext = item.password_ciphertext
    host.private_key_ciphertext = item.private_key_ciphertext
    host.private_key_passphrase_ciphertext = item.private_key_passphrase_ciphertext
    host.connect_timeout_ms = item.connect_timeout_ms
    host.is_active = item.enabled
    host.remark = item.remark
    db.commit()
    db.refresh(host)
    return _public_host(_host_from_model(host))


def upsert_server_action(payload: EmergencyServerActionItem, db: Optional[Session] = None) -> Dict:
    if db is None:
        config = _load_json_config()
        config.server_actions = [x for x in config.server_actions if x.action_code != payload.action_code] + [payload]
        save_emergency_config(config)
        return payload.dict()

    runbook = db.query(Runbook).filter(Runbook.runbook_code == payload.action_code).first()
    if not runbook:
        runbook = Runbook(runbook_code=payload.action_code)
        db.add(runbook)
    runbook.runbook_name = payload.action_name
    runbook.runbook_type = 'server'
    runbook.target_host_id = _resolve_host_id(db, payload.target_host_code)
    runbook.script_type = payload.script_type
    runbook.script_body = payload.script_body
    runbook.confirm_text = payload.confirm_text
    runbook.enabled = payload.enabled
    runbook.remark = payload.remark
    db.commit()
    db.refresh(runbook)
    return payload.dict()


def upsert_db_action(payload: EmergencyDbActionItem, db: Optional[Session] = None) -> Dict:
    if db is None:
        config = _load_json_config()
        config.database_actions = [x for x in config.database_actions if x.action_code != payload.action_code] + [payload]
        save_emergency_config(config)
        return payload.dict()

    runbook = db.query(Runbook).filter(Runbook.runbook_code == payload.action_code).first()
    if not runbook:
        runbook = Runbook(runbook_code=payload.action_code)
        db.add(runbook)
    runbook.runbook_name = payload.action_name
    runbook.runbook_type = 'database'
    runbook.target_host_id = _resolve_host_id(db, payload.target_host_code)
    runbook.script_type = payload.script_type
    runbook.script_body = payload.script_body
    runbook.enabled = payload.enabled
    runbook.remark = payload.remark
    db.commit()
    db.refresh(runbook)
    return payload.dict()


def upsert_process_action(payload: EmergencyProcessActionItem, db: Optional[Session] = None) -> Dict:
    if db is None:
        config = _load_json_config()
        config.process_actions = [x for x in config.process_actions if x.action_code != payload.action_code] + [payload]
        save_emergency_config(config)
        return payload.dict()

    runbook = db.query(Runbook).filter(Runbook.runbook_code == payload.action_code).first()
    if not runbook:
        runbook = Runbook(runbook_code=payload.action_code)
        db.add(runbook)
    runbook.runbook_name = payload.action_name
    runbook.runbook_type = 'process'
    runbook.target_host_id = _resolve_host_id(db, payload.target_host_code)
    runbook.script_type = payload.script_type
    runbook.script_body = payload.script_body
    runbook.enabled = payload.enabled
    runbook.remark = payload.remark
    db.commit()
    db.refresh(runbook)
    return payload.dict()


def import_emergency_json_to_db(db: Session) -> Dict:
    config = _load_json_config()
    imported = {
        'ssh_hosts': 0,
        'server_actions': 0,
        'database_actions': 0,
        'process_actions': 0,
    }
    for item in config.ssh_hosts:
        upsert_ssh_host(EmergencySshHostSaveRequest(**item.dict()), db=db)
        imported['ssh_hosts'] += 1
    for item in config.server_actions:
        upsert_server_action(item, db=db)
        imported['server_actions'] += 1
    for item in config.database_actions:
        upsert_db_action(item, db=db)
        imported['database_actions'] += 1
    for item in config.process_actions:
        upsert_process_action(item, db=db)
        imported['process_actions'] += 1
    return imported
