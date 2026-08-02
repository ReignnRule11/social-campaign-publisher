import hmac, hashlib, os, json
from fastapi.testclient import TestClient
from app.main import app
from sqlmodel import SQLModel, create_engine, Session
from app.models import SocialPostEntry, Campaign

client = TestClient(app)


def make_sig(secret: str, body: bytes) -> str:
    mac = hmac.new(secret.encode('utf-8'), msg=body, digestmod=hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def test_webhook_valid_and_invalid():
    # ensure DB exists in test app by hitting startup event
    # ensure app DB has tables
    from app.db import get_engine
    from app.models import init_db
    real_engine = get_engine()
    init_db(real_engine)

    # create a SocialPostEntry directly in the app DB
    with Session(real_engine) as session:
        cam = Campaign(title="T", body="B", status="scheduled")
        session.add(cam)
        session.commit()
        session.refresh(cam)
        spe = SocialPostEntry(campaign_id=cam.id, platform="x", platform_post_id="p-123", status="queued")
        session.add(spe)
        session.commit()

    payload = {"platform_post_id": "p-123", "status": "delivered"}
    body = json.dumps(payload).encode('utf-8')
    secret = os.getenv('WEBHOOK_SECRET', 'webhook-secret')
    sig = make_sig(secret, body)

    r = client.post('/api/webhooks/social-delivery', data=body, headers={'X-Signature': sig, 'Content-Type': 'application/json'})
    assert r.status_code == 200

    # check DB updated
    from app.db import get_engine as ge2
    from sqlmodel import select
    with Session(ge2()) as session:
        stmt = session.exec(select(SocialPostEntry).where(SocialPostEntry.platform_post_id == "p-123")).first()
        assert stmt.status == "published"

    # forged signature
    bad = client.post('/api/webhooks/social-delivery', data=body, headers={'X-Signature': 'sha256=deadbeef', 'Content-Type': 'application/json'})
    assert bad.status_code == 400
