from typing import Optional
from sqlmodel import Session, select
from app.models import IdempotencyRecord
import json
from datetime import datetime


def get_idempotency(session: Session, key: str, platform: str) -> Optional[IdempotencyRecord]:
    if not key:
        return None
    stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.idempotency_key == key,
        IdempotencyRecord.platform == platform,
    )
    return session.exec(stmt).first()


def create_idempotency(session: Session, key: str, platform: str, response: dict) -> IdempotencyRecord:
    rec = IdempotencyRecord(idempotency_key=key, platform=platform, response=json.dumps(response), created_at=datetime.utcnow())
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


def ensure_idempotent(session: Session, key: Optional[str], platform: str, publish_fn):
    """If record exists, return it. Otherwise call publish_fn(), store result, and return it.

    publish_fn is a callable that performs the actual adapter publish and returns a dict.
    """
    if key:
        existing = get_idempotency(session, key, platform)
        if existing:
            try:
                return json.loads(existing.response), False
            except Exception:
                return {"error": "bad-stored-response"}, False
    result = publish_fn()
    if key:
        create_idempotency(session, key, platform, result)
    return result, True
