"""Shared FastAPI dependencies."""

from typing import Annotated

import jwt
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.errors import APIError
from ..core.security import decode_access_token
from ..models import User

# tokenUrl points at the login route so /docs shows the Authorize button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

UnauthorizedError = APIError(
    "Not authenticated",
    status_code=status.HTTP_401_UNAUTHORIZED,
    code="unauthorized",
)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise UnauthorizedError
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError from exc

    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError
    if not user.is_active:
        raise APIError(
            "Account is deactivated",
            status_code=status.HTTP_403_FORBIDDEN,
            code="account_disabled",
        )
    return user
