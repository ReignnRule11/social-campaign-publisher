from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class Campaign(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    body: str
    scheduled_at: Optional[str] = None
    status: str = "draft"

class SocialPostEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int
    platform: str
    platform_post_id: Optional[str] = None
    status: str = "queued"
    # store arbitrary metadata as a JSON column; avoid naming collision with SQLModel.metadata
    metadata_json: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    retries: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IdempotencyRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    idempotency_key: str = Field(index=True)
    platform: str = Field(index=True)
    response: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TokenStorage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str
    encrypted_token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


def init_db(engine):
    SQLModel.metadata.create_all(engine)
    # quick migration: ensure 'retries' column exists on socialpostentry for older DBs
    try:
        from sqlalchemy import inspect, text
        insp = inspect(engine)
        if 'socialpostentry' in insp.get_table_names():
            cols = [c['name'] for c in insp.get_columns('socialpostentry')]
            if 'retries' not in cols:
                # add column with default 0
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE socialpostentry ADD COLUMN retries INTEGER DEFAULT 0'))
                    conn.commit()
    except Exception:
        # best-effort only; if this fails, user should run migrations separately
        pass
