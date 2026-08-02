import hmac
import hashlib


def verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    """Verify HMAC-SHA256 signature header.

    signature_header expected format: 'sha256=<hex>' or raw hex.
    """
    if not secret:
        return False
    sig = signature_header or ""
    if sig.startswith("sha256="):
        sig = sig.split("=", 1)[1]
    try:
        sig_bytes = bytes.fromhex(sig)
    except Exception:
        return False
    mac = hmac.new(secret.encode('utf-8'), msg=body, digestmod=hashlib.sha256)
    expected = mac.digest()
    return hmac.compare_digest(expected, sig_bytes)
