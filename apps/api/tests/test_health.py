"""Health endpoint tests and standard error shape checks."""

from opportunity_api.core.errors import ErrorResponse


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_returns_ok(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_standard_error_model(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert ErrorResponse.model_validate(body)
    assert body["error"]["code"] == "not_found"
    assert body["error"]["details"] is None
