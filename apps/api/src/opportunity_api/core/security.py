"""Verify Supabase access tokens using project JWKS or an explicit legacy secret."""

from functools import lru_cache

import jwt

from .config import get_settings


@lru_cache(maxsize=8)
def _jwks_client(project_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{project_url}/auth/v1/.well-known/jwks.json", timeout=5, lifespan=300)


def decode_supabase_token(token: str) -> dict:
    """Validate signature, expiration, issuer, audience and required identity claims."""
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("Supabase auth is not configured: set APP_SUPABASE_URL")
    project_url = settings.supabase_url.rstrip("/")
    algorithm = jwt.get_unverified_header(token).get("alg")
    if algorithm in ("ES256", "RS256"):
        # Trust only this configured project's keys; never token-provided jku/x5u URLs.
        signing_key = _jwks_client(project_url).get_signing_key_from_jwt(token)
        if signing_key.algorithm_name != algorithm:
            raise jwt.InvalidAlgorithmError("Signing key algorithm mismatch")
        key = signing_key.key
    elif algorithm == "HS256" and settings.supabase_jwt_secret:
        key = settings.supabase_jwt_secret
    else:
        raise jwt.InvalidAlgorithmError("Unsupported or unconfigured JWT algorithm")
    return jwt.decode(
        token,
        key,
        algorithms=[algorithm],
        audience=settings.supabase_jwt_audience,
        issuer=f"{project_url}/auth/v1",
        options={"require": ["exp", "sub", "iss", "aud"]},
    )
