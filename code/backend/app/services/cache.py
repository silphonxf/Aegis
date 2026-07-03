from __future__ import annotations

import json
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import get_logger

try:
    import redis
except Exception:  # pragma: no cover - optional runtime dependency
    redis = None


logger = get_logger("cache")
_client = None


def _enabled() -> bool:
    return bool(settings.REDIS_CACHE_ENABLED) and settings.APP_ENV != "test"


def get_client():
    global _client
    if not _enabled() or redis is None:
        return None
    if _client is not None:
        return _client
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
    except Exception as exc:
        logger.warning("Redis 缓存不可用，回退数据库读取: %s", exc)
        return None
    _client = client
    return _client


def get_json(key: str) -> Optional[Any]:
    client = get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("读取 Redis 缓存失败: key=%s error=%s", key, exc)
        return None


def set_json(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    client = get_client()
    if client is None:
        return
    ttl = ttl_seconds if ttl_seconds is not None else settings.REDIS_CACHE_TTL_SECONDS
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        if ttl and ttl > 0:
            client.setex(key, ttl, payload)
        else:
            client.set(key, payload)
    except Exception as exc:
        logger.warning("写入 Redis 缓存失败: key=%s error=%s", key, exc)


def delete_prefix(prefix: str) -> int:
    client = get_client()
    if client is None:
        return 0
    deleted = 0
    try:
        for key in client.scan_iter(f"{prefix}*"):
            deleted += int(client.delete(key) or 0)
    except Exception as exc:
        logger.warning("清理 Redis 缓存失败: prefix=%s error=%s", prefix, exc)
    return deleted
