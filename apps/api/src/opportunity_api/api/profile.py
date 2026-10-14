"""Profile and skills endpoints (skills double as interests on the profile)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.errors import APIError
from ..models import Skill, User
from ..schemas.profile import ProfilePatch, ProfileResponse, ProfileUpsert
from ..schemas.skill import SkillAdd, SkillResponse, SkillsReplace
from .deps import get_current_user, get_or_create_profile

router = APIRouter(prefix="/profile", tags=["profile"])
skills_router = APIRouter(tags=["skills"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Db = Annotated[Session, Depends(get_db)]


def _normalize_skill_name(name: str) -> str:
    return name.strip().lower()


def _get_or_create_skill(db: Session, name: str) -> Skill:
    skill = db.scalar(select(Skill).where(func.lower(Skill.name) == name))
    if skill is None:
        skill = Skill(name=name)
        db.add(skill)
        db.flush()
    return skill


@router.get("", response_model=ProfileResponse)
def get_profile(db: Db, current_user: CurrentUser) -> ProfileResponse:
    profile = get_or_create_profile(db, current_user)
    db.commit()
    return profile


@router.put("", response_model=ProfileResponse)
def replace_profile(db: Db, current_user: CurrentUser, payload: ProfileUpsert) -> ProfileResponse:
    profile = get_or_create_profile(db, current_user)
    data = payload.model_dump()
    for field, value in data.items():
        setattr(profile, field, value)
    db.commit()
    return profile


@router.patch("", response_model=ProfileResponse)
def update_profile(db: Db, current_user: CurrentUser, payload: ProfilePatch) -> ProfileResponse:
    profile = get_or_create_profile(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    return profile


@router.get("/skills", response_model=list[SkillResponse])
def get_my_skills(db: Db, current_user: CurrentUser) -> list[Skill]:
    return sorted(current_user.skills, key=lambda skill: skill.name)


@router.put("/skills", response_model=list[SkillResponse])
def replace_my_skills(db: Db, current_user: CurrentUser, payload: SkillsReplace) -> list[Skill]:
    names = {_normalize_skill_name(name) for name in payload.names if name.strip()}
    current_user.skills = [_get_or_create_skill(db, name) for name in sorted(names)]
    db.commit()
    return sorted(current_user.skills, key=lambda skill: skill.name)


@router.post("/skills", response_model=list[SkillResponse], status_code=status.HTTP_201_CREATED)
def add_my_skill(db: Db, current_user: CurrentUser, payload: SkillAdd) -> list[Skill]:
    skill = _get_or_create_skill(db, _normalize_skill_name(payload.name))
    if skill not in current_user.skills:
        current_user.skills.append(skill)
        db.commit()
    return sorted(current_user.skills, key=lambda s: s.name)


@router.delete("/skills/{name}", response_model=list[SkillResponse])
def remove_my_skill(db: Db, current_user: CurrentUser, name: str) -> list[Skill]:
    skill = db.scalar(select(Skill).where(func.lower(Skill.name) == _normalize_skill_name(name)))
    if skill is None or skill not in current_user.skills:
        raise APIError("Skill not found on profile", status_code=404, code="skill_not_found")
    current_user.skills.remove(skill)
    db.commit()
    return sorted(current_user.skills, key=lambda s: s.name)


@skills_router.get("/skills", response_model=list[SkillResponse])
def list_skills(db: Db) -> list[Skill]:
    return list(db.scalars(select(Skill).order_by(Skill.name)))
