"""Eligibility API schemas: statuses, per-rule results, engine inputs/outputs."""

import enum

from pydantic import BaseModel, ConfigDict, Field

from opportunity_api.models.opportunity import OpportunityDegreeLevel
from opportunity_api.models.profile import DegreeLevel


class EligibilityStatus(enum.StrEnum):
    """Final vocabulary for A9. Do not add synonyms."""

    eligible = "eligible"
    possibly_eligible = "possibly_eligible"
    not_eligible = "not_eligible"
    unknown = "unknown"


class RuleResult(BaseModel):
    """Outcome of one eligibility rule, including the why."""

    model_config = ConfigDict(str_strip_whitespace=True)

    rule: str = Field(min_length=1)
    status: EligibilityStatus
    reason: str = Field(min_length=1)


class EligibilityResult(BaseModel):
    """Combined eligibility decision plus every rule's evidence."""

    status: EligibilityStatus
    reasons: list[RuleResult]


class StudentInput(BaseModel):
    """What we know about the student. Missing facts stay ``None`` (unknown)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    degree_level: DegreeLevel | None = None
    study_year: int | None = Field(default=None, ge=1, le=7)
    graduation_year: int | None = Field(default=None, ge=1900, le=2100)
    location: str | None = Field(default=None, max_length=255)


class OpportunityInput(BaseModel):
    """Structured requirements of one opportunity.

    ``graduation_years`` is reserved for future structured data; no source
    provides it today, so the graduation rule currently reports ``unknown``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    degree_level: OpportunityDegreeLevel | None = None
    study_year: list[int] | None = None
    location: str | None = Field(default=None, max_length=255)
    graduation_years: list[int] | None = None
