from sqlmodel import SQLModel, create_engine, Session
from app.services.publish import publish_campaign
from app.models import Campaign, TokenStorage, SocialPostEntry
from app.utils.crypto import encrypt_token
import os


def test_publish_with_simulated_429():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # create campaign
        cam = Campaign(title="T", body="B", status="scheduled")
        session.add(cam)
        session.commit()
        session.refresh(cam)

        # call publish with a platform that signals simulate_429
        platforms = [{"platform": "x", "encrypted_token": "dummy", "simulate_429": True}]
        results = publish_campaign(session, cam.id, platforms, idempotency_key="k1")
        assert len(results) == 1
        res = results[0]["result"]
        assert res.get("status") == "rate_limited"

        # check SocialPostEntry recorded with status rate_limited
        from sqlmodel import select
        spe_list = session.exec(select(SocialPostEntry).where(SocialPostEntry.campaign_id == cam.id)).all()
        assert len(spe_list) == 1
        assert spe_list[0].status == "rate_limited"
