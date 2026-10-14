"""Shared FastAPI dependencies."""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.errors import APIError
from ..core.security import decode_supabase_token
from ..models import Profile, User

# Bearer tokens are issued by Supabase Auth, not by a backend login endpoint.
bearer_scheme = HTTPBearer(auto_error=False)

UnauthorizedError = APIError(
    "Not authenticated",
    status_code=status.HTTP_401_UNAUTHORIZED,
    code="unauthorized",
)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if creds is None:
        raise UnauthorizedError
    try:
        claims = decode_supabase_token(creds.credentials)
        user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise UnauthorizedError from exc

    user = db.get(User, user_id)
    if user is None:
        # First sight of this Supabase user — mirror the row locally.
        metadata = claims.get("user_metadata") or {}
        email = claims.get("email") or metadata.get("email") or ""
        user = User(id=user_id, email=email, full_name=metadata.get("full_name") or "")
        db.add(user)
        db.flush()
    if not user.is_active:
        raise APIError(
            "Account is deactivated",
            status_code=status.HTTP_403_FORBIDDEN,
            code="account_disabled",
        )
    get_or_create_profile(db, user)
    db.commit()
    return user


def get_or_create_profile(db: Session, user: User) -> Profile:
    """Return the user's profile, creating an empty row on first use (bootstrap)."""
    if user.profile is None:
        profile = Profile()
        user.profile = profile
        db.add(profile)
        db.flush()
        return profile
    return user.profile
