"""Validation of Supabase-issued JWT access tokens.

The backend never issues tokens or handles passwords — Supabase Auth (GoTrue)
signs access tokens client-side and this module only verifies them.
"""

import jwt

from .config import get_settings

ALGORITHM = "HS256"


def decode_supabase_token(token: str) -> dict:
    """Verify a Supabase-issued JWT and return its claims.

    Validates the HS256 signature, `exp`, `iss` (must equal
    `{supabase_url}/auth/v1`) and `aud`. Raises jwt.PyJWTError on any
    invalid or expired token.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_jwt_secret:
        raise RuntimeError(
            "Supabase auth is not configured: set APP_SUPABASE_URL and APP_SUPABASE_JWT_SECRET"
        )
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=[ALGORITHM],
        audience=settings.supabase_jwt_audience,
        issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
    )
