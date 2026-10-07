"""Registration, login, and current-user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.database import get_db
from ..core.errors import APIError
from ..core.security import create_access_token, hash_password, verify_password
from ..models import User
from ..schemas import TokenResponse, UserCreate, UserResponse
from .deps import get_current_user, get_or_create_profile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise APIError(
            "Email is already registered",
            status_code=status.HTTP_409_CONFLICT,
            code="email_taken",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.flush()
    get_or_create_profile(db, user)
    db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == form.username))
    if user is None or not verify_password(form.password, user.password_hash):
        raise APIError(
            "Invalid email or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
        )
    if not user.is_active:
        raise APIError(
            "Account is deactivated",
            status_code=status.HTTP_403_FORBIDDEN,
            code="account_disabled",
        )
    get_or_create_profile(db, user)
    db.commit()
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
