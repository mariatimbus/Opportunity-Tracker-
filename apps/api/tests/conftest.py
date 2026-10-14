"""Test fixtures: TestClient backed by an in-memory sqlite database with all tables."""

import os

os.environ["DATABASE_URL"] = "sqlite://"  # in-memory, per-connection

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from opportunity_api.core.database import Base, get_db
from opportunity_api.main import create_app


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


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    """Register (or log in) a user and return Authorization headers."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    if response.status_code == 409:  # already registered in this test
        response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code in (200, 201), response.text
    if response.status_code == 201:
        token = client.post(
            "/api/v1/auth/login", data={"username": email, "password": password}
        ).json()["access_token"]
    else:
        token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
