from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.shared_data import EmergencyHost, Runbook
from app.models.system import System, SystemUserBinding
from app.models.tool_task import ToolTask
from app.models.user import User
from app.schemas.emergency_config import (
    EmergencyDbActionItem,
    EmergencyOpsConfig,
    EmergencyProcessActionItem,
    EmergencyServerActionItem,
    EmergencySshHostItem,
    EmergencySshHostSaveRequest,
)

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "emergency_ops.json"


def _ensure_parent():
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _mask_secret(value: str | None) -> str | None:
    return "***" if value else None


def _encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    key = os.getenv("AEGIS_CREDENTIALS_MASTER_KEY") or os.getenv("AEGIS_SECRET_KEY") or settings.SECRET_KEY
    payload = f"{key}:{value}".encode("utf-8")
    return "ENC:" + base64.b64encode(payload).decode("ascii")


def _public_host(item: EmergencySshHostItem) -> Dict:
    data = item.dict()
    data["has_password"] = bool(data.get("password_ciphertext"))
    data["has_private_key"] = bool(data.get("private_key_ciphertext"))
    data["password_ciphertext"] = _mask_secret(data.get("password_ciphertext"))
    data["private_key_ciphertext"] = _mask_secret(data.get("private_key_ciphertext"))
    data["private_key_passphrase_ciphertext"] = _mask_secret(data.get("private_key_passphrase_ciphertext"))
    return data


def _load_json_config() -> EmergencyOpsConfig:
    if not _CONFIG_PATH.exists():
        return EmergencyOpsConfig()
    raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    return EmergencyOpsConfig(**raw)


def save_emergency_config(config: EmergencyOpsConfig) -> None:
    _ensure_parent()
    _CONFIG_PATH.write_text(json.dumps(config.dict(), ensure_ascii=False, indent=2), encoding="utf-8")


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
        system_id=item.system_id,
        enabled=item.is_active,
        remark=item.remark,
        has_password=bool(item.password_ciphertext),
        has_private_key=bool(item.private_key_ciphertext),
    )


def _server_action_from_runbook(item: Runbook, host_code: str) -> EmergencyServerActionItem:
    return EmergencyServerActionItem(
        action_code=item.runbook_code,
        action_name=item.runbook_name,
        target_host_code=host_code,
        module_type="server",
        action_category=item.action_category or "reboot_host",
        system_id=item.system_id,
        admin_user_id=item.admin_user_id,
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
        module_type="database",
        db_type="mysql",
        system_id=item.system_id,
        admin_user_id=item.admin_user_id,
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
        module_type="process",
        action_category=item.action_category or "restart_process",
        system_id=item.system_id,
        admin_user_id=item.admin_user_id,
        target_host_code=host_code,
        process_name=item.process_name or item.runbook_name,
        process_id_source="fixed" if item.default_process_id else "runtime_detect",
        default_process_id=item.default_process_id,
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
        host_code = host.host_code if host else ""
        if rb.runbook_type == "server" and host_code:
            server_actions.append(_server_action_from_runbook(rb, host_code))
        elif rb.runbook_type == "database":
            database_actions.append(_db_action_from_runbook(rb, host_code or None))
        elif rb.runbook_type == "process" and host_code:
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
        "ssh_hosts": [_public_host(item) for item in config.ssh_hosts],
        "server_actions": [item.dict() for item in config.server_actions],
        "database_actions": [item.dict() for item in config.database_actions],
        "process_actions": [item.dict() for item in config.process_actions],
    }


def _resolve_host_id(db: Session, host_code: Optional[str]) -> Optional[int]:
    if not host_code:
        return None
    host = db.query(EmergencyHost).filter(EmergencyHost.host_code == host_code).first()
    if not host:
        raise HTTPException(status_code=404, detail={"code": "EMERGENCY_HOST_NOT_FOUND", "message": "目标 SSH 主机不存在"})
    return host.id


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
        system_id=payload.system_id,
        enabled=payload.enabled,
        remark=payload.remark,
    )
    if db is None:
        config = _load_json_config()
        config.ssh_hosts = [x for x in config.ssh_hosts if x.host_code != item.host_code] + [item]
        save_emergency_config(config)
        return _public_host(item)

    host = db.query(EmergencyHost).filter(EmergencyHost.host_code == item.host_code).first()
    previous_password = host.password_ciphertext if host else None
    previous_private_key = host.private_key_ciphertext if host else None
    previous_passphrase = host.private_key_passphrase_ciphertext if host else None
    if not host:
        host = EmergencyHost(host_code=item.host_code)
        db.add(host)
    host.host_name = item.host_name
    host.host_ip = item.host_ip
    host.port = item.port
    host.username = item.username
    host.auth_type = item.auth_type
    host.password_ciphertext = item.password_ciphertext or previous_password
    host.private_key_ciphertext = item.private_key_ciphertext or previous_private_key
    host.private_key_passphrase_ciphertext = item.private_key_passphrase_ciphertext or previous_passphrase
    host.connect_timeout_ms = item.connect_timeout_ms
    host.system_id = item.system_id
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
    runbook.runbook_type = "server"
    runbook.action_category = payload.action_category
    runbook.system_id = payload.system_id
    runbook.target_host_id = _resolve_host_id(db, payload.target_host_code)
    runbook.admin_user_id = payload.admin_user_id
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
    runbook.runbook_type = "database"
    runbook.action_category = "database"
    runbook.system_id = payload.system_id
    runbook.target_host_id = _resolve_host_id(db, payload.target_host_code) if payload.target_host_code else None
    runbook.admin_user_id = payload.admin_user_id
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
    runbook.runbook_type = "process"
    runbook.action_category = payload.action_category
    runbook.system_id = payload.system_id
    runbook.target_host_id = _resolve_host_id(db, payload.target_host_code)
    runbook.admin_user_id = payload.admin_user_id
    runbook.process_name = payload.process_name
    runbook.default_process_id = payload.default_process_id
    runbook.script_type = payload.script_type
    runbook.script_body = payload.script_body
    runbook.enabled = payload.enabled
    runbook.remark = payload.remark
    db.commit()
    db.refresh(runbook)
    return payload.dict()


def import_emergency_json_to_db(db: Session) -> Dict:
    config = _load_json_config()
    imported = {"ssh_hosts": 0, "server_actions": 0, "database_actions": 0, "process_actions": 0}
    for item in config.ssh_hosts:
        upsert_ssh_host(EmergencySshHostSaveRequest(**item.dict()), db=db)
        imported["ssh_hosts"] += 1
    for item in config.server_actions:
        upsert_server_action(item, db=db)
        imported["server_actions"] += 1
    for item in config.database_actions:
        upsert_db_action(item, db=db)
        imported["database_actions"] += 1
    for item in config.process_actions:
        upsert_process_action(item, db=db)
        imported["process_actions"] += 1
    return imported


def _runbook_public_item(item: Runbook, host: Optional[EmergencyHost], system: Optional[System]) -> Dict:
    return {
        "id": item.id,
        "action_code": item.runbook_code,
        "action_name": item.runbook_name,
        "action_category": item.action_category,
        "runbook_type": item.runbook_type,
        "system_id": item.system_id,
        "system_name": system.name if system else None,
        "host_name": host.host_name if host else None,
        "host_ip": host.host_ip if host else None,
        "target_host_code": host.host_code if host else None,
        "process_name": item.process_name,
        "default_process_id": item.default_process_id,
        "confirm_text": item.confirm_text,
        "risk_level": item.risk_level,
        "enabled": item.enabled,
    }


def list_mobile_emergency_actions(db: Session, user: User) -> Dict:
    hosts = {item.id: item for item in db.query(EmergencyHost).filter(EmergencyHost.is_active.is_(True)).all()}
    systems = {item.id: item for item in db.query(System).filter(System.is_active.is_(True)).all()}
    owner_system_ids = {
        row.system_id
        for row in db.query(SystemUserBinding)
        .filter(SystemUserBinding.user_id == user.id, SystemUserBinding.binding_role == "owner")
        .all()
    }
    owner_system_ids.update(item.id for item in systems.values() if item.owner_user_id == user.id)

    rows = db.query(Runbook).filter(Runbook.enabled.is_(True)).order_by(Runbook.id.asc()).all()
    server_actions = []
    process_actions = []
    database_actions = []
    for rb in rows:
        host = hosts.get(rb.target_host_id) if rb.target_host_id else None
        system = systems.get(rb.system_id) if rb.system_id else None
        item = _runbook_public_item(rb, host, system)
        if rb.runbook_type == "server":
            if user.role.code == "super_admin" or rb.admin_user_id == user.id:
                server_actions.append(item)
        elif rb.runbook_type == "process":
            if user.role.code == "super_admin" or rb.admin_user_id == user.id or rb.system_id in owner_system_ids:
                process_actions.append(item)
        elif rb.runbook_type == "database":
            if user.role.code == "super_admin" or rb.admin_user_id == user.id or rb.system_id in owner_system_ids:
                database_actions.append(item)
    return {
        "server_actions": server_actions,
        "process_actions": process_actions,
        "database_actions": database_actions,
        "submenus": [
            {"key": "server_reboot", "label": "系统重启", "count": len(server_actions)},
            {"key": "app_restart", "label": "应用重启", "count": len(process_actions)},
            {"key": "db_deadlock", "label": "数据库死锁处理", "count": len(database_actions)},
        ],
    }


def create_emergency_task(db: Session, user: User, action_code: str) -> Dict:
    rb = db.query(Runbook).filter(Runbook.runbook_code == action_code, Runbook.enabled.is_(True)).first()
    if not rb:
        raise HTTPException(status_code=404, detail={"code": "RUNBOOK_NOT_FOUND", "message": "应急动作不存在或已停用"})
    visible = list_mobile_emergency_actions(db, user)
    allowed_codes = {item["action_code"] for group in ("server_actions", "process_actions", "database_actions") for item in visible[group]}
    if action_code not in allowed_codes:
        raise HTTPException(status_code=403, detail={"code": "RUNBOOK_FORBIDDEN", "message": "无权执行该应急动作"})
    host = db.query(EmergencyHost).filter(EmergencyHost.id == rb.target_host_id).first() if rb.target_host_id else None
    target = host.host_name if host else rb.runbook_name
    task = ToolTask(
        action=rb.action_category or rb.runbook_type,
        target=target,
        status="pending_approval",
        executor=user.username,
        result=json.dumps(
            {
                "runbook_code": rb.runbook_code,
                "runbook_name": rb.runbook_name,
                "runbook_type": rb.runbook_type,
                "action_category": rb.action_category,
                "system_id": rb.system_id,
                "target_host_id": rb.target_host_id,
                "script_type": rb.script_type,
                "script_body": rb.script_body,
            },
            ensure_ascii=False,
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"task_id": task.id, "status": task.status, "action_code": rb.runbook_code, "action_name": rb.runbook_name, "target": target}
