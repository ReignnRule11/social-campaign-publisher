from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional
import os
from app.utils.webhook import verify_signature
from sqlmodel import Session, select
from app.db import get_engine
from app.models import SocialPostEntry

router = APIRouter()
WEBHOOK_SECRET_ENV = "WEBHOOK_SECRET"

@router.post("/social-delivery")
async def social_delivery(request: Request, x_signature: Optional[str] = Header(None)):
    body = await request.body()
    secret = os.getenv(WEBHOOK_SECRET_ENV)
    if not verify_signature(secret or "", body, x_signature or ""):
        raise HTTPException(status_code=400, detail="invalid signature")
    payload = await request.json()
    platform_post_id = payload.get("platform_post_id")
    status = payload.get("status")
    if not platform_post_id:
        raise HTTPException(status_code=400, detail="missing platform_post_id")

    engine = get_engine()
    with Session(engine) as session:
        stmt = select(SocialPostEntry).where(SocialPostEntry.platform_post_id == platform_post_id)
        spe = session.exec(stmt).first()
        if not spe:
            raise HTTPException(status_code=404, detail="post not found")
        # map platform status to local status
        if status == "delivered" or status == "published":
            spe.status = "published"
        else:
            spe.status = "failed"
        session.add(spe)
        session.commit()
    return {"ok": True}
