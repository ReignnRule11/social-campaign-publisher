from typing import Dict, Any
from .base import SocialPublisher
import time


class FakePlatformPublisher(SocialPublisher):
    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    def publish(self, campaign: Dict[str, Any], idempotency_key: str | None = None) -> Dict[str, Any]:
        # Simulate network latency
        time.sleep(0.05)
        # Simulated platform post id
        platform_post_id = f"{self.platform_name}-post-{int(time.time()*1000)}"
        return {"platform_post_id": platform_post_id, "status": "ok"}


class FakeInstagramPublisher(FakePlatformPublisher):
    def __init__(self):
        super().__init__("instagram")


class FakeXPublisher(FakePlatformPublisher):
    def __init__(self):
        super().__init__("x")
