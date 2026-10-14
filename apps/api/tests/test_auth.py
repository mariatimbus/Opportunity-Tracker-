"""Auth tests: Supabase JWT validation and local user upsert on /auth/me."""

import uuid

from opportunity_api.models import User
from tests.conftest import TEST_JWT_SECRET, mint_token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _existing_user(db_factory, email="ada@example.com") -> User:
    user = User(id=uuid.uuid4(), email=email, full_name="Ada Lovelace")
    with db_factory() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_register_and_login_endpoints_are_removed(client):
    assert client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "password": "supersecret1", "full_name": "X"},
    ).status_code == 404
    assert client.post(
        "/api/v1/auth/login", data={"username": "x@example.com", "password": "supersecret1"}
    ).status_code == 404


def test_me_returns_current_user_with_valid_token(client, db_factory):
    user = _existing_user(db_factory)
    token = mint_token(sub=str(user.id), email=user.email, full_name=user.full_name)
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == "ada@example.com"


def test_me_upserts_unknown_user_from_claims(client, db_factory):
    user_id = uuid.uuid4()
    token = mint_token(sub=str(user_id), email="new@example.com", full_name="New User")
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 200
    with db_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        assert user.email == "new@example.com"
        assert user.full_name == "New User"
        assert user.profile is not None  # profile bootstrapped


def test_me_falls_back_to_user_metadata_email(client, db_factory):
    user_id = uuid.uuid4()
    token = mint_token(
        sub=str(user_id),
        include_email=False,
        user_metadata={"email": "meta@example.com", "full_name": "Meta User"},
    )
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 200
    with db_factory() as session:
        assert session.get(User, user_id).email == "meta@example.com"


def test_me_rejects_token_with_wrong_secret(client, db_factory):
    user = _existing_user(db_factory)
    token = mint_token(sub=str(user.id), secret="some-other-secret")
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_rejects_expired_token(client, db_factory):
    user = _existing_user(db_factory)
    token = mint_token(sub=str(user.id), expires_in=-1)
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 401


def test_me_rejects_wrong_audience(client, db_factory):
    user = _existing_user(db_factory)
    token = mint_token(sub=str(user.id), audience="not-authenticated")
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 401


def test_me_rejects_wrong_issuer(client, db_factory):
    user = _existing_user(db_factory)
    token = mint_token(sub=str(user.id), issuer="https://evil.example.com/auth/v1")
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 401


def test_me_rejects_missing_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_rejects_malformed_token(client):
    response = client.get("/api/v1/auth/me", headers=_bearer("not-a-jwt"))
    assert response.status_code == 401


def test_me_rejects_token_without_sub(client):
    token = mint_token(include_sub=False)
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 401


def test_inactive_user_gets_403(client, db_factory):
    user = _existing_user(db_factory)
    with db_factory() as session:
        session.get(User, user.id).is_active = False
        session.commit()
    token = mint_token(sub=str(user.id), email=user.email, full_name=user.full_name)
    response = client.get("/api/v1/auth/me", headers=_bearer(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_disabled"


def test_settings_use_supabase_test_config():
    from opportunity_api.core.config import get_settings

    settings = get_settings()
    assert settings.supabase_jwt_secret == TEST_JWT_SECRET
    assert settings.supabase_jwt_audience == "authenticated"
    assert settings.supabase_url == "https://test.supabase.co"


def test_users_table_has_no_password_hash_column(db_factory):
    from sqlalchemy import inspect

    with db_factory():
        columns = [c.name for c in inspect(User).c]
    assert "password_hash" not in columns
