"""Pydantic request/response schemas."""

from .application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
    OpportunitySummary,
)
from .opportunity import OpportunityResponse, PaginatedOpportunityResponse
from .profile import ProfilePatch, ProfileResponse, ProfileUpsert
from .skill import SkillAdd, SkillResponse, SkillsReplace
from .user import UserResponse

__all__ = [
    "ApplicationCreate",
    "ApplicationListResponse",
    "ApplicationResponse",
    "ApplicationUpdate",
    "OpportunityResponse",
    "OpportunitySummary",
    "PaginatedOpportunityResponse",
    "ProfilePatch",
    "ProfileResponse",
    "ProfileUpsert",
    "SkillAdd",
    "SkillResponse",
    "SkillsReplace",
    "UserResponse",
]
