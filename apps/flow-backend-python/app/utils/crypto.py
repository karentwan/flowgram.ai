"""AES-256-GCM encryption helpers — byte-for-byte compatible with Node backend.

Mirrors `apps/flow-backend/src/lib/crypto.ts` exactly:
  - Master key: base64-decoded FLOWGRAM_ENCRYPTION_KEY (must be 32 bytes).
  - Payload format: ``enc::`` prefix + base64( iv(12) || tag(16) || ciphertext ).
  - Encrypt is NOT idempotent (random IV each call); decrypt short-circuits on
    the ``enc::`` prefix.

Cross-backend invariant: a value encrypted by Node decrypts here, and vice
versa. See test_crypto.py for the interop test vector.
"""

from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings

# All constants MUST match Node's crypto.ts.
_ALGO_KEY_LEN = 32  # AES-256
_IV_LEN = 12  # 96-bit nonce (GCM standard)
_TAG_LEN = 16  # 128-bit auth tag
PREFIX = "enc::"


class CryptoConfigError(RuntimeError):
    """Raised when FLOWGRAM_ENCRYPTION_KEY is missing or malformed."""


def _load_key() -> bytes:
    """Decode the master key, enforcing the 32-byte length (matches Node KEY_BUFFER)."""
    raw_b64 = get_settings().flowgram_encryption_key
    if not raw_b64:
        raise CryptoConfigError(
            "FLOWGRAM_ENCRYPTION_KEY is not set. Generate a 32-byte base64 value with:\n"
            "  python -c \"import secrets, base64; "
            "print(base64.b64encode(secrets.token_bytes(32)).decode())\""
        )
    try:
        key = base64.b64decode(raw_b64, validate=True)
    except Exception as e:
        raise CryptoConfigError("FLOWGRAM_ENCRYPTION_KEY is not valid base64") from e
    if len(key) != _ALGO_KEY_LEN:
        raise CryptoConfigError(
            f"FLOWGRAM_ENCRYPTION_KEY must decode to {_ALGO_KEY_LEN} bytes "
            f"(got {len(key)}). Generate a fresh one — see the error above."
        )
    return key


def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string into an opaque ``enc::<base64>`` payload.

    Matches Node's encrypt(): random 12-byte IV, AES-256-GCM, output
    ``enc::base64(iv || tag || ciphertext)``. Empty input returns empty
    (matches Node's `if (!plaintext) return plaintext`).
    """
    if not plaintext:
        return plaintext
    key = _load_key()
    iv = os.urandom(_IV_LEN)  # cryptographically secure random nonce
    # AESGCM.encrypt returns ciphertext || tag (tag appended). Node's layout is
    # iv || tag || ciphertext, so we split the tag off the end and reorder.
    ct_and_tag = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), associated_data=None)
    ciphertext = ct_and_tag[:-_TAG_LEN]
    tag = ct_and_tag[-_TAG_LEN:]
    payload = iv + tag + ciphertext  # matches Node's Buffer.concat([iv, tag, data])
    return PREFIX + base64.b64encode(payload).decode("ascii")


def decrypt(payload: str) -> str:
    """Decrypt an ``enc::<base64>`` payload. Returns original UTF-8 string.

    Non-payload values pass through unchanged (matches Node's decrypt()).
    Raises InvalidTag if the payload is corrupt or the key is wrong.
    """
    if not payload or not payload.startswith(PREFIX):
        return payload
    key = _load_key()
    raw = base64.b64decode(payload[len(PREFIX):])
    iv = raw[:_IV_LEN]
    tag = raw[_IV_LEN:_IV_LEN + _TAG_LEN]
    ciphertext = raw[_IV_LEN + _TAG_LEN:]
    # cryptography's AESGCM expects ciphertext || tag (tag appended), so we
    # reconstruct that ordering from Node's iv || tag || ciphertext layout.
    try:
        plaintext = AESGCM(key).decrypt(iv, ciphertext + tag, associated_data=None)
    except InvalidTag:
        raise
    return plaintext.decode("utf-8")


def is_encrypted(value: object) -> bool:
    """True if the value looks like an encrypted payload (matches Node isEncrypted)."""
    return isinstance(value, str) and value.startswith(PREFIX)
