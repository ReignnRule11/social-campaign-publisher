import os
import time
from typing import Dict, Any
from app.utils.crypto import decrypt_token
from .base import SocialPublisher

FAKE_PLATFORM_URL = os.getenv("FAKE_PLATFORM_URL", "http://localhost:4000")

class RealPlatformPublisher(SocialPublisher):
    """A minimal 'real' adapter stub that demonstrates decrypting a stored token and using it.

    This does not call external services in this scaffold; instead it shows the expected flow:
    - decrypt token
    - include idempotency key in request metadata
    - handle simulated rate-limit via a flag in campaign metadata
    """
    def __init__(self, platform_name: str, encrypted_token: str | None = None):
        self.platform_name = platform_name
        self.encrypted_token = encrypted_token

    def _get_bearer(self) -> str | None:
        if not self.encrypted_token:
            return None
        try:
            return decrypt_token(self.encrypted_token)
        except Exception:
            return None

    def publish(self, campaign: Dict[str, Any], idempotency_key: str | None = None) -> Dict[str, Any]:
        # decrypt token (if present)
        token = self._get_bearer()
        # simulate reading campaign metadata to trigger a fake 429 path
        simulate_429 = campaign.get("simulate_429", False)
        time.sleep(0.05)
        if simulate_429:
            # signal rate-limit back to caller so the worker may backoff
            return {"status": "rate_limited", "retry_after": 2}
        # otherwise return a successful post id and include idempotency hint
        platform_post_id = f"{self.platform_name}-post-{int(time.time()*1000)}"
        return {"platform_post_id": platform_post_id, "status": "ok", "used_token": bool(token), "idempotency_key": idempotency_key}


class RealInstagramPublisher(RealPlatformPublisher):
    def __init__(self, encrypted_token: str | None = None):
        super().__init__("instagram", encrypted_token)


class RealXPublisher(RealPlatformPublisher):
    def __init__(self, encrypted_token: str | None = None):
        super().__init__("x", encrypted_token)
