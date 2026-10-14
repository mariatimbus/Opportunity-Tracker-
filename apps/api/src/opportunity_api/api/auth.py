"""Current-user endpoints. Sign-up and sign-in happen against Supabase Auth."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..models import User
from ..schemas import UserResponse
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
