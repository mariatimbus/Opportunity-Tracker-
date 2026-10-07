"""Profile request/response schemas with Bachelor/Master field validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from opportunity_api.models.profile import DegreeLevel

GRADUATION_YEAR_MIN = 1900
GRADUATION_YEAR_MAX = 2100


def _validate_degree_level(value: str | None) -> str | None:
    if value is not None and value not in DegreeLevel.__members__:
        allowed = ", ".join(DegreeLevel.__members__)
        raise ValueError(f"degree_level must be one of: {allowed}")
    return value


def _validate_graduation_year(value: int | None) -> int | None:
    if value is not None and not (GRADUATION_YEAR_MIN <= value <= GRADUATION_YEAR_MAX):
        raise ValueError(
            f"graduation_year must be between {GRADUATION_YEAR_MIN} and {GRADUATION_YEAR_MAX}"
        )
    return value


class ProfileResponse(BaseModel):
    """Full profile representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    headline: str | None
    bio: str | None
    location: str | None
    resume_url: str | None
    degree_level: str | None
    field_of_study: str | None
    university: str | None
    graduation_year: int | None
    created_at: datetime
    updated_at: datetime


class ProfileUpsert(BaseModel):
    """Full replacement payload for PUT /profile. Omitted fields are cleared."""

    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = None
    location: str | None = Field(default=None, max_length=255)
    resume_url: str | None = Field(default=None, max_length=512)
    degree_level: str | None = None
    field_of_study: str | None = Field(default=None, max_length=255)
    university: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = None

    _v_degree = field_validator("degree_level")(_validate_degree_level)
    _v_year = field_validator("graduation_year")(_validate_graduation_year)


class ProfilePatch(BaseModel):
    """Partial update payload for PATCH /profile. Only sent fields change."""

    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = None
    location: str | None = Field(default=None, max_length=255)
    resume_url: str | None = Field(default=None, max_length=512)
    degree_level: str | None = None
    field_of_study: str | None = Field(default=None, max_length=255)
    university: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = None

    _v_degree = field_validator("degree_level")(_validate_degree_level)
    _v_year = field_validator("graduation_year")(_validate_graduation_year)
