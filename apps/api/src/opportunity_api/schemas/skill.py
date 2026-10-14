"""Skill request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class SkillAdd(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SkillsReplace(BaseModel):
    """Replace the user's whole skill set. An empty list clears it."""

    names: list[str] = Field(default_factory=list, max_length=100)
