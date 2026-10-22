"""Matching schemas: explainable score output and engine inputs (A10).

A score is never a bare number: it ships with the eligibility status that
gated it, the per-component breakdown, and the reasons behind each
component. All of it deterministic — no AI, no embeddings (that is A11/A12).
"""

from pydantic import BaseModel, ConfigDict, Field

from opportunity_api.models.opportunity import OpportunityDegreeLevel
from opportunity_api.models.profile import DegreeLevel
from opportunity_api.schemas.eligibility import EligibilityStatus


class ComponentScores(BaseModel):
    """Points per explainable component. Each is capped in ``scoring.py``."""

    skills: int = 0
    field_fit: int = 0
    interests: int = 0
    location: int = 0


class MatchResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    score: int = Field(ge=0, le=100)
    eligibility: EligibilityStatus
    components: ComponentScores
    reasons: list[str]


class MatchingProfile(BaseModel):
    """What we know about the student. Reuses the A9 eligibility fields."""

    model_config = ConfigDict(str_strip_whitespace=True)

    degree_level: DegreeLevel | None = None
    study_year: int | None = Field(default=None, ge=1, le=7)
    graduation_year: int | None = Field(default=None, ge=1900, le=2100)
    location: str | None = Field(default=None, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class MatchingOpportunity(BaseModel):
    """What we know about the opportunity."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    degree_level: OpportunityDegreeLevel | None = None
    study_year: list[int] | None = None
    skills: list[str] = Field(default_factory=list)
