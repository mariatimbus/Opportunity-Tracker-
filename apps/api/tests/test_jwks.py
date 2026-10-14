"""Real asymmetric signatures with a fixture JWKS, no network or signing secrets."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from opportunity_api.core import security
from tests.conftest import TEST_SUPABASE_URL


@pytest.fixture()
def es256_token(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
    jwk.update(kid="fixture", alg="ES256", use="sig")
    jwks_client = jwt.PyJWKClient(f"{TEST_SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(jwks_client, "fetch_data", lambda: {"keys": [jwk]})
    monkeypatch.setattr(security, "_jwks_client", lambda url: jwks_client)

    def mint(**changes):
        claims = {
            "sub": str(uuid.uuid4()),
            "iss": f"{TEST_SUPABASE_URL}/auth/v1",
            "aud": "authenticated",
            "email": "fixture@example.com",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            **changes,
        }
        return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": "fixture"})

    return mint


def test_es256_valid_token(client, es256_token):
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {es256_token()}"}
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://untrusted.invalid/auth/v1"},
        {"aud": "service_role"},
        {"exp": datetime(2000, 1, 1, tzinfo=UTC)},
    ],
)
def test_es256_invalid_claims(client, es256_token, changes):
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {es256_token(**changes)}"}
        ).status_code
        == 401
    )


def test_es256_tampering(client, es256_token):
    token = es256_token()
    header, payload, signature = token.split(".")
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {header}.{payload}.{signature}"}
        ).status_code
        == 401
    )


def test_es256_unknown_key(client, es256_token, monkeypatch):
    token = es256_token()

    def missing_key(token):
        raise jwt.PyJWKClientError("Unknown signing key")

    monkeypatch.setattr(
        security._jwks_client(TEST_SUPABASE_URL), "get_signing_key_from_jwt", missing_key
    )
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )
