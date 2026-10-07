"""Auth endpoint tests: register, login, token protection, user bootstrap."""

from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from sqlalchemy import delete, select

from opportunity_api.core.config import get_settings
from opportunity_api.core.security import decode_access_token
from opportunity_api.models import Profile, User


def _register(client, email="ada@example.com", password="supersecret1", name="Ada Lovelace"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )


def _login(client, email="ada@example.com", password="supersecret1"):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


def _token(client, **kwargs) -> str:
    _register(client, **kwargs)
    return _login(client, **kwargs).json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_user_and_201(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Lovelace"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_register_bootstraps_empty_profile(client, db_factory):
    _register(client)
    with db_factory() as session:
        profile = session.scalar(select(Profile))
        assert profile is not None
        assert profile.headline is None


def test_register_rejects_duplicate_email(client):
    _register(client)
    response = _register(client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_register_rejects_short_password(client):
    response = _register(client, password="short")
    assert response.status_code == 422


def test_login_returns_bearer_token(client):
    _register(client)
    response = _login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] == get_settings().jwt_expire_minutes * 60


def test_login_rejects_wrong_password(client):
    _register(client)
    response = _login(client, password="wrongpassword")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_rejects_unknown_email(client):
    assert _login(client).status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    registered = _register(client).json()
    token = _login(client).json()["access_token"]
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]


def test_me_rejects_missing_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_rejects_garbage_token(client):
    response = client.get("/api/v1/auth/me", headers=_bearer("not-a-jwt"))
    assert response.status_code == 401


def test_me_rejects_expired_token(client):
    _register(client)
    user_id = decode_access_token(_login(client).json()["access_token"])
    settings = get_settings()
    expired = pyjwt.encode(
        {"sub": str(user_id), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    response = client.get("/api/v1/auth/me", headers=_bearer(expired))
    assert response.status_code == 401


def test_me_rejects_token_for_deleted_user(client, db_factory):
    token = _token(client)
    with db_factory() as session:
        session.execute(delete(User))
        session.commit()
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 401


def test_inactive_user_cannot_authenticate(client, db_factory):
    token = _token(client)
    with db_factory() as session:
        user = session.scalar(select(User).where(User.email == "ada@example.com"))
        user.is_active = False
        session.commit()
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_disabled"
    assert _login(client).status_code == 403
