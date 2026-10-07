"""Database engine, session factory, and the get_db dependency.

The engine is created lazily so the app boots even when no database is reachable
(e.g. for liveness probes); /health/db reports connectivity separately.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_db() -> Generator[Session]:
    """FastAPI dependency yielding a database session.

    The engine is built on first use; if the database is unreachable the session
    creation will fail and callers (e.g. /health/db) handle the error.
    """
    _get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
