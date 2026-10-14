"""Rate limiting middleware tests."""

from fastapi.testclient import TestClient

from opportunity_api.core.config import get_settings
from opportunity_api.core.database import get_db
from opportunity_api.main import create_app


def test_rate_limit_returns_429_after_limit(db_factory, monkeypatch):
    monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    try:
        app = create_app()

        def override_get_db():
            with db_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        # Health checks are never counted.
        assert client.get("/health").status_code == 200

        assert client.get("/api/v1/skills").status_code == 200
        assert client.get("/api/v1/skills").status_code == 200
        response = client.get("/api/v1/skills")
        assert response.status_code == 429
        assert response.json() == {
            "error": {
                "code": "rate_limited",
                "message": "Rate limit exceeded. Try again later.",
                "details": None,
            }
        }
        # Health checks stay reachable even after the limit is hit.
        assert client.get("/health/db").status_code == 200
    finally:
        get_settings.cache_clear()
