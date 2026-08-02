import os
from typing import Generator
from sqlmodel import Session, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
_engine = create_engine(DATABASE_URL, echo=False)


def get_engine():
    return _engine


def get_session() -> Generator[Session, None, None]:
    with Session(_engine) as session:
        yield session
