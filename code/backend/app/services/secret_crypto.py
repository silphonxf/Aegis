from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Optional

from app.core.config import settings


def _b64e(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _master_key() -> bytes:
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def _derive_key(salt: bytes, purpose: bytes) -> bytes:
    return hmac.new(_master_key(), salt + purpose, hashlib.sha256).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        blocks.append(hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = value.encode("utf-8")
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    enc_key = _derive_key(salt, b"enc")
    mac_key = _derive_key(salt, b"mac")
    cipher = bytes(a ^ b for a, b in zip(raw, _keystream(enc_key, nonce, len(raw))))
    tag = hmac.new(mac_key, nonce + cipher, hashlib.sha256).digest()
    return "v1:" + ":".join(_b64e(part) for part in (salt, nonce, cipher, tag))


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        version, salt_text, nonce_text, cipher_text, tag_text = value.split(":", 4)
        if version != "v1":
            return None
        salt = _b64d(salt_text)
        nonce = _b64d(nonce_text)
        cipher = _b64d(cipher_text)
        tag = _b64d(tag_text)
    except Exception:
        return None

    enc_key = _derive_key(salt, b"enc")
    mac_key = _derive_key(salt, b"mac")
    expected = hmac.new(mac_key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        return None
    raw = bytes(a ^ b for a, b in zip(cipher, _keystream(enc_key, nonce, len(cipher))))
    return raw.decode("utf-8")
