from typing import List, Dict, Optional
from sqlmodel import Session
from app.models import Campaign, SocialPostEntry
from app.adapters.fake_adapter import FakeInstagramPublisher, FakeXPublisher
from app.adapters.real_adapter import RealInstagramPublisher, RealXPublisher
from app.services.idempotency import ensure_idempotent


def _get_adapter(platform: str, encrypted_token: Optional[str] = None):
    # Prefer the 'real' adapter when an encrypted token is provided; otherwise use the fake
    if platform == "instagram":
        if encrypted_token:
            return RealInstagramPublisher(encrypted_token)
        return FakeInstagramPublisher()
    if platform == "x":
        if encrypted_token:
            return RealXPublisher(encrypted_token)
        return FakeXPublisher()
    raise ValueError(f"Unknown platform: {platform}")


def publish_campaign(session: Session, campaign_id: int, platforms: List[Dict], idempotency_key: Optional[str] = None) -> List[Dict]:
    """Publish the given campaign to each platform entry in platforms.

    platforms is a list of dicts: {"platform": "instagram", "encrypted_token": <opt>}.
    For each platform:
      - choose adapter
      - call ensure_idempotent(session, composed_key, platform, publish_fn)
      - persist a SocialPostEntry with the adapter response

    Returns a list of results per platform.
    """
    cam = session.get(Campaign, campaign_id)
    if not cam:
        raise ValueError("campaign not found")

    results = []
    for p in platforms:
        platform_name = p.get("platform")
        encrypted_token = p.get("encrypted_token")
        adapter = _get_adapter(platform_name, encrypted_token)

        # Compose an idempotency key: prefer provided key + platform, else campaign-<id>
        composed_key = (idempotency_key or f"campaign-{campaign_id}") + f":{platform_name}"

        def _do_publish():
            # include any simulation flags from the platform dict (e.g., simulate_429) so tests can exercise adapter behaviour
            campaign_payload = {"id": cam.id, "title": cam.title, "body": cam.body}
            if p.get("simulate_429"):
                campaign_payload["simulate_429"] = True
            return adapter.publish(campaign_payload, idempotency_key=composed_key)

        res, created = ensure_idempotent(session, composed_key, platform_name, _do_publish)

        # persist SocialPostEntry (store response in metadata_json)
        spe = SocialPostEntry(
            campaign_id=cam.id,
            platform=platform_name,
            platform_post_id=res.get("platform_post_id"),
            status=("published" if res.get("status") == "ok" else res.get("status")),
            metadata_json=res,
            retries=0,
        )
        session.add(spe)
        session.commit()
        session.refresh(spe)

        results.append({"platform": platform_name, "result": res, "idempotency_created": created, "social_post_entry_id": spe.id})

    return results
