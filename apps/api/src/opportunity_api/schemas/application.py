"""Application (saved opportunity / tracker entry) schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from opportunity_api.models.application import ApplicationStatus
from opportunity_api.models.opportunity import OpportunityType


class OpportunitySummary(BaseModel):
    """Embedded opportunity details for tracker views (avoids N lookups)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    organization: str | None
    opportunity_type: OpportunityType
    deadline: datetime | None


class ApplicationCreate(BaseModel):
    opportunity_id: UUID
    status: ApplicationStatus = ApplicationStatus.saved
    notes: str | None = None
    applied_at: datetime | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    applied_at: datetime | None = None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    opportunity_id: UUID
    status: ApplicationStatus
    notes: str | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    opportunity: OpportunitySummary


class ApplicationListResponse(BaseModel):
    items: list[ApplicationResponse] = Field(default_factory=list)
    total: int
