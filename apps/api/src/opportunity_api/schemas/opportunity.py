"""Opportunity response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from opportunity_api.models.opportunity import OpportunityDegreeLevel, OpportunityType

from .skill import SkillResponse


class OpportunityResponse(BaseModel):
    """Full opportunity representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    organization: str | None
    opportunity_type: OpportunityType
    location: str | None
    url: str
    source: str
    source_id: str
    deadline: datetime | None
    posted_at: datetime | None
    is_active: bool
    degree_level: OpportunityDegreeLevel | None
    study_year: list[int] | None
    skills: list[SkillResponse]


class PaginatedOpportunityResponse(BaseModel):
    items: list[OpportunityResponse]
    page: int
    page_size: int
    total: int
