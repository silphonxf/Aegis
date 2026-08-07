from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

import app.db.session as db_session_module
from app.core.config import settings
from app.models.ai_engine_config import AIEngineConfig
from app.services.secret_crypto import decrypt_secret, encrypt_secret


def _first_config(db: Session) -> Optional[AIEngineConfig]:
    return db.query(AIEngineConfig).order_by(AIEngineConfig.id.asc()).first()


def _defaults() -> Dict[str, Any]:
    provider = settings.AI_PROVIDER.lower()
    if provider == "openclaw":
        return {
            "engine_type": "openclaw",
            "base_url": settings.OPENCLAW_BASE_URL or "",
            "api_key": settings.OPENCLAW_API_KEY or "",
            "model": settings.OPENCLAW_MODEL,
            "timeout_seconds": settings.OPENCLAW_TIMEOUT_SECONDS,
            "chat_path": settings.OPENCLAW_RESPONSES_PATH,
            "diagnose_path": settings.OPENCLAW_RESPONSES_PATH,
            "log_analyze_path": settings.OPENCLAW_RESPONSES_PATH,
            "enabled": True,
        }
    if provider == "internal_gateway":
        engine_type = "pi_gateway" if settings.INTERNAL_AI_GATEWAY_PROVIDER.lower() in {"pi_gateway", "pi-gateway"} else "internal_gateway"
        return {
            "engine_type": engine_type,
            "provider": settings.INTERNAL_AI_GATEWAY_PROVIDER,
            "base_url": settings.INTERNAL_AI_GATEWAY_BASE_URL or "",
            "api_key": settings.INTERNAL_AI_GATEWAY_API_KEY or "",
            "model": settings.INTERNAL_AI_GATEWAY_MODEL,
            "timeout_seconds": settings.INTERNAL_AI_GATEWAY_TIMEOUT_SECONDS,
            "chat_path": settings.INTERNAL_AI_GATEWAY_CHAT_PATH,
            "diagnose_path": settings.INTERNAL_AI_GATEWAY_DIAGNOSE_PATH,
            "log_analyze_path": settings.INTERNAL_AI_GATEWAY_LOG_ANALYZE_PATH,
            "enabled": True,
        }
    return {
        "engine_type": "offline",
        "base_url": "",
        "api_key": "",
        "model": settings.OFFLINE_AI_MODEL,
        "timeout_seconds": settings.OFFLINE_AI_TIMEOUT_SECONDS,
        "chat_path": "",
        "diagnose_path": "",
        "log_analyze_path": "",
        "enabled": True,
    }


def serialize_ai_engine_config(db: Session) -> Dict[str, Any]:
    row = _first_config(db)
    if not row:
        data = _defaults()
        return {
            **data,
            "has_api_key": bool(data.get("api_key")),
            "api_key": "",
            "source": "env",
        }
    return {
        "engine_type": row.engine_type,
        "base_url": row.base_url or "",
        "api_key": "",
        "has_api_key": bool(row.api_key_encrypted),
        "model": row.model or "",
        "timeout_seconds": row.timeout_seconds,
        "chat_path": row.chat_path or "",
        "diagnose_path": row.diagnose_path or "",
        "log_analyze_path": row.log_analyze_path or "",
        "enabled": row.enabled,
        "source": "db",
        "updated_at": row.updated_at,
    }


def get_runtime_ai_config() -> Dict[str, Any]:
    db = db_session_module.SessionLocal()
    try:
        row = _first_config(db)
        if not row or not row.enabled:
            return _defaults()
        return {
            "engine_type": row.engine_type,
            "provider": settings.INTERNAL_AI_GATEWAY_PROVIDER if row.engine_type == "internal_gateway" else row.engine_type,
            "base_url": row.base_url or "",
            "api_key": decrypt_secret(row.api_key_encrypted) or "",
            "model": row.model or "",
            "timeout_seconds": row.timeout_seconds,
            "chat_path": row.chat_path or "",
            "diagnose_path": row.diagnose_path or "",
            "log_analyze_path": row.log_analyze_path or "",
            "enabled": row.enabled,
        }
    finally:
        db.close()


def upsert_ai_engine_config(db: Session, payload: Any) -> Dict[str, Any]:
    row = _first_config(db)
    is_new = row is None
    if not row:
        row = AIEngineConfig()
        db.add(row)

    row.engine_type = payload.engine_type
    row.base_url = payload.base_url or None
    if payload.api_key is not None:
        row.api_key_encrypted = encrypt_secret(payload.api_key.strip()) if payload.api_key.strip() else None
    elif is_new:
        default_api_key = str(_defaults().get("api_key") or "").strip()
        if default_api_key:
            row.api_key_encrypted = encrypt_secret(default_api_key)
    row.model = payload.model or None
    row.timeout_seconds = payload.timeout_seconds
    row.chat_path = payload.chat_path or None
    row.diagnose_path = payload.diagnose_path or None
    row.log_analyze_path = payload.log_analyze_path or None
    row.enabled = payload.enabled
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return serialize_ai_engine_config(db)
