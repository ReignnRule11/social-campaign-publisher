from sqlmodel import SQLModel, create_engine, Session
from app.services.idempotency import ensure_idempotent
from app.models import IdempotencyRecord


def test_ensure_idempotent_creates_and_reuses():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        calls = {"count": 0}
        def publisher():
            calls["count"] += 1
            return {"platform_post_id": "p-1", "status": "ok"}

        # first call: should create record and call publisher
        result, created = ensure_idempotent(session, "key-123", "instagram", publisher)
        assert created is True
        assert result["platform_post_id"] == "p-1"
        assert calls["count"] == 1

        # second call: should reuse stored response and not call publisher again
        result2, created2 = ensure_idempotent(session, "key-123", "instagram", publisher)
        assert created2 is False
        assert result2["platform_post_id"] == "p-1"
        assert calls["count"] == 1
