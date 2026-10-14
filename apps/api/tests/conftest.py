"""Test fixtures: TestClient backed by an in-memory sqlite database with all tables."""

import os
import uuid
from datetime import UTC, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"  # in-memory, per-connection
os.environ["APP_SUPABASE_URL"] = "https://test.supabase.co"
os.environ["APP_SUPABASE_JWT_SECRET"] = "test-jwt-secret"

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from opportunity_api.core.database import Base, get_db
from opportunity_api.main import create_app

TEST_SUPABASE_URL = os.environ["APP_SUPABASE_URL"]
TEST_JWT_SECRET = os.environ["APP_SUPABASE_JWT_SECRET"]


def mint_token(
    *,
    sub: str | None = None,
    email: str = "ada@example.com",
    full_name: str = "Test User",
    secret: str = TEST_JWT_SECRET,
    audience: str = "authenticated",
    expires_in: int = 3600,
    issuer: str = f"{TEST_SUPABASE_URL}/auth/v1",
    include_sub: bool = True,
    include_email: bool = True,
    **extra: object,
) -> str:
    """Mint a Supabase-shaped HS256 JWT for tests (the backend only validates)."""
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "user_metadata": {"full_name": full_name},
        **extra,
    }
    if include_sub:
        claims["sub"] = sub or str(uuid.uuid4())
    if include_email:
        claims["email"] = email
    return pyjwt.encode(claims, secret, algorithm="HS256")


def auth_headers(client: TestClient, email: str, full_name: str = "Test User") -> dict[str, str]:
    """Return Authorization headers for a (possibly new) user backed by a minted token.

    The first authenticated request upserts the local User row.
    """
    return {"Authorization": f"Bearer {mint_token(email=email, full_name=full_name)}"}


@pytest.fixture()
def db_factory():
    """Fresh in-memory database (single shared connection) per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory():
        yield factory
    engine.dispose()


@pytest.fixture()
def client(db_factory) -> TestClient:
    app = create_app()

    def override_get_db():
        with db_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
