from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.firewall import FirewallBlockConfig
from app.services.secret_crypto import decrypt_secret, encrypt_secret


@dataclass
class FirewallRuntimeConfig:
    enabled: bool
    scheme: str
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    verify_ssl: bool
    timeout_seconds: int
    address_book_name: str
    addrbook_path: str


def _first_config(db: Session) -> Optional[FirewallBlockConfig]:
    return db.query(FirewallBlockConfig).order_by(FirewallBlockConfig.id.asc()).first()


def get_runtime_firewall_config(db: Optional[Session]) -> FirewallRuntimeConfig:
    row = _first_config(db) if db is not None else None
    if row:
        return FirewallRuntimeConfig(
            enabled=row.enabled,
            scheme=row.scheme or "https",
            host=row.firewall_ip,
            port=row.port,
            username=decrypt_secret(row.username_encrypted),
            password=decrypt_secret(row.password_encrypted),
            verify_ssl=row.verify_ssl,
            timeout_seconds=row.timeout_seconds,
            address_book_name=row.address_book_name,
            addrbook_path=row.addrbook_path or "/api/addrbook",
        )

    return FirewallRuntimeConfig(
        enabled=settings.HILLSTONE_ENABLED,
        scheme=settings.HILLSTONE_SCHEME,
        host=settings.HILLSTONE_HOST,
        port=settings.HILLSTONE_PORT,
        username=settings.HILLSTONE_USERNAME,
        password=settings.HILLSTONE_PASSWORD,
        verify_ssl=settings.HILLSTONE_VERIFY_SSL,
        timeout_seconds=settings.HILLSTONE_TIMEOUT_SECONDS,
        address_book_name=settings.HILLSTONE_ADDRESS_BOOK_NAME,
        addrbook_path=settings.HILLSTONE_ADDRBOOK_PATH,
    )


def serialize_firewall_config(db: Session) -> Dict[str, Any]:
    row = _first_config(db)
    if row:
        return {
            "source": "database",
            "enabled": row.enabled,
            "scheme": row.scheme,
            "firewall_ip": row.firewall_ip,
            "port": row.port,
            "address_book_name": row.address_book_name,
            "verify_ssl": row.verify_ssl,
            "timeout_seconds": row.timeout_seconds,
            "addrbook_path": row.addrbook_path,
            "has_username": bool(row.username_encrypted),
            "has_password": bool(row.password_encrypted),
            "updated_at": row.updated_at,
        }

    return {
        "source": "env",
        "enabled": settings.HILLSTONE_ENABLED,
        "scheme": settings.HILLSTONE_SCHEME,
        "firewall_ip": settings.HILLSTONE_HOST,
        "port": settings.HILLSTONE_PORT,
        "address_book_name": settings.HILLSTONE_ADDRESS_BOOK_NAME,
        "verify_ssl": settings.HILLSTONE_VERIFY_SSL,
        "timeout_seconds": settings.HILLSTONE_TIMEOUT_SECONDS,
        "addrbook_path": settings.HILLSTONE_ADDRBOOK_PATH,
        "has_username": bool(settings.HILLSTONE_USERNAME),
        "has_password": bool(settings.HILLSTONE_PASSWORD),
        "updated_at": None,
    }


def upsert_firewall_config(db: Session, payload: Any) -> Dict[str, Any]:
    row = _first_config(db)
    if not row:
        row = FirewallBlockConfig(
            enabled=payload.enabled,
            scheme=payload.scheme,
            firewall_ip=payload.firewall_ip,
            port=payload.port,
            address_book_name=payload.address_book_name,
            verify_ssl=payload.verify_ssl,
            timeout_seconds=payload.timeout_seconds,
            addrbook_path=payload.addrbook_path,
        )
        db.add(row)

    row.enabled = payload.enabled
    row.scheme = payload.scheme
    row.firewall_ip = payload.firewall_ip
    row.port = payload.port
    row.address_book_name = payload.address_book_name
    row.verify_ssl = payload.verify_ssl
    row.timeout_seconds = payload.timeout_seconds
    row.addrbook_path = payload.addrbook_path
    if payload.username is not None:
        row.username_encrypted = encrypt_secret(payload.username.strip()) if payload.username.strip() else None
    if payload.password is not None:
        row.password_encrypted = encrypt_secret(payload.password) if payload.password else None
    row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return serialize_firewall_config(db)
