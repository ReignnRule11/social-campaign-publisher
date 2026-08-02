from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.db import get_session
from sqlmodel import Session
from app.models import Campaign
from app.db import get_engine

router = APIRouter()

class CampaignCreate(BaseModel):
    title: str
    body: str


@router.post("/")
def create_campaign(payload: CampaignCreate, idempotency_key: Optional[str] = Header(None), session: Session = Depends(get_session)):
    """Create a campaign record (stub). Persists to DB; scheduling to be implemented.

    Accepts an optional Idempotency-Key header which will be used later by the publishing flow.
    """
    cam = Campaign(title=payload.title, body=payload.body, status="scheduled")
    session.add(cam)
    session.commit()
    session.refresh(cam)
    return {"message": "campaign created", "id": cam.id, "title": cam.title, "idempotency_key_received": bool(idempotency_key)}


class PublishRequest(BaseModel):
    platforms: list


@router.post("/{campaign_id}/publish")
def publish_campaign_endpoint(campaign_id: int, payload: PublishRequest, idempotency_key: Optional[str] = Header(None), session: Session = Depends(get_session)):
    """Trigger publish for a campaign to the requested platforms.

    platforms: list of dicts: {"platform": "instagram", "token_id": <optional>, "simulate_429": <optional bool>}
    If token_id is present, the stored encrypted token is looked up and passed to the adapter.
    """
    from app.models import TokenStorage
    platforms_resolved = []
    for p in payload.platforms:
        platform_name = p.get("platform")
        token_id = p.get("token_id")
        encrypted_token = None
        if token_id:
            tok = session.get(TokenStorage, token_id)
            if not tok:
                raise HTTPException(status_code=404, detail=f"token {token_id} not found")
            encrypted_token = tok.encrypted_token
        entry = {"platform": platform_name, "encrypted_token": encrypted_token}
        if p.get("simulate_429"):
            entry["simulate_429"] = True
        platforms_resolved.append(entry)

    from app.services.publish import publish_campaign as _publish
    results = _publish(session, campaign_id, platforms_resolved, idempotency_key=idempotency_key)
    return {"results": results}
