import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SECRET_KEY_ENV = "SECRET_KEY"


def _get_key() -> bytes:
    b = os.getenv(SECRET_KEY_ENV)
    if not b:
        raise RuntimeError(f"Environment variable {SECRET_KEY_ENV} must be set to a 32-byte base64 or raw key")
    # Allow raw bytes or base64-encoded
    try:
        # try base64 decode
        key = base64.b64decode(b)
    except Exception:
        key = b.encode()
    if len(key) not in (16, 24, 32):
        raise RuntimeError("SECRET_KEY must decode to 16, 24 or 32 bytes for AES")
    return key


def encrypt_token(plaintext: str) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    payload = nonce + ct
    return base64.b64encode(payload).decode('utf-8')


def decrypt_token(token_b64: str) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    payload = base64.b64decode(token_b64)
    nonce = payload[:12]
    ct = payload[12:]
    pt = aesgcm.decrypt(nonce, ct, None)
    return pt.decode('utf-8')
