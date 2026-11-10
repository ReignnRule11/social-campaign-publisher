import os
from typing import Generator

from sqlmodel import Session, create_engine


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, connect_args=_connect_args)


def get_engine():
    return _engine


def get_session() -> Generator[Session, None, None]:
    with Session(_engine) as session:
        yield session
