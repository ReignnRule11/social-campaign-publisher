from abc import ABC, abstractmethod
from typing import Any, Dict

class SocialPublisher(ABC):
    """Adapter interface: publish campaign to a platform.

    Implementations must be safe to call multiple times when used with an idempotency guard.
    """

    @abstractmethod
    def publish(self, campaign: Dict[str, Any], idempotency_key: str | None = None) -> Dict[str, Any]:
        """Publish a campaign to the platform.

        Returns a dict containing at least: platform_post_id, status
        """
        raise NotImplementedError()
