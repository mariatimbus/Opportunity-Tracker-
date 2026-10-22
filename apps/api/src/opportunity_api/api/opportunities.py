"""Opportunity catalog endpoints: paginated list with filters and detail by id."""

from datetime import datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..core.config import get_settings
from ..core.database import get_db
from ..core.errors import APIError
from ..eligibility import evaluate as evaluate_eligibility
from ..matching import AIScorer, OllamaEmbedder, score_match
from ..matching.engine import to_opportunity_input
from ..models import Opportunity, OpportunityDegreeLevel, OpportunityType, Profile, User
from ..schemas import OpportunityResponse, PaginatedOpportunityResponse
from ..schemas.eligibility import EligibilityResult, StudentInput
from ..schemas.matching import MatchingOpportunity, MatchingProfile, MatchResult
from .deps import get_current_user

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

Db = Annotated[Session, Depends(get_db)]

MAX_PAGE_SIZE = 100
# Newest first; nulls last so unposted opportunities sink to the end.
_ORDER = (Opportunity.posted_at.desc().nullslast(), Opportunity.id)


def _apply_filters(
    stmt: Select,
    *,
    opportunity_type: OpportunityType | None,
    degree_level: OpportunityDegreeLevel | None,
    location: str | None,
    is_active: bool | None,
    deadline_after: datetime | None,
    deadline_before: datetime | None,
    search: str | None,
) -> Select:
    if opportunity_type is not None:
        stmt = stmt.where(Opportunity.opportunity_type == opportunity_type)
    if degree_level is not None:
        # A specific degree matches itself and "both"; null (unknown) never
        # matches a degree filter.
        if degree_level is OpportunityDegreeLevel.both:
            stmt = stmt.where(Opportunity.degree_level == degree_level)
        else:
            stmt = stmt.where(
                Opportunity.degree_level.in_([degree_level, OpportunityDegreeLevel.both])
            )
    if location:
        stmt = stmt.where(Opportunity.location.ilike(f"%{location}%"))
    if is_active is not None:
        stmt = stmt.where(Opportunity.is_active == is_active)
    if deadline_after is not None:
        stmt = stmt.where(Opportunity.deadline >= deadline_after)
    if deadline_before is not None:
        stmt = stmt.where(Opportunity.deadline <= deadline_before)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Opportunity.title.ilike(pattern),
                Opportunity.organization.ilike(pattern),
                Opportunity.description.ilike(pattern),
            )
        )
    return stmt


@router.get("", response_model=PaginatedOpportunityResponse)
def list_opportunities(
    db: Db,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    opportunity_type: OpportunityType | None = None,
    degree_level: OpportunityDegreeLevel | None = None,
    study_year: Annotated[int | None, Query(ge=1, le=6)] = None,
    location: str | None = None,
    is_active: bool | None = None,
    deadline_after: datetime | None = None,
    deadline_before: datetime | None = None,
    search: str | None = None,
) -> PaginatedOpportunityResponse:
    filters = dict(
        opportunity_type=opportunity_type,
        degree_level=degree_level,
        location=location,
        is_active=is_active,
        deadline_after=deadline_after,
        deadline_before=deadline_before,
        search=search,
    )
    total_stmt = _apply_filters(select(func.count()).select_from(Opportunity), **filters)
    total = db.scalar(total_stmt)

    # The study_year containment filter is applied in Python (see below), so
    # its total must be recomputed there too; keep the SQL count for the rest.
    stmt = _apply_filters(select(Opportunity), **filters)
    if study_year is None:
        # Two queries (count + page) are intentional: cheap at MVP volumes and
        # far simpler than a window-function count over the same filter set.
        items = db.scalars(
            stmt.options(selectinload(Opportunity.skills))
            .order_by(*_ORDER)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
    else:
        # Containment filter: on Postgres this should become a jsonb @>
        # predicate; sqlite (tests/dev) filters in memory — fine at MVP
        # volumes. null study_year means unknown and never matches.
        matches = [
            opportunity
            for opportunity in db.scalars(
                stmt.options(selectinload(Opportunity.skills)).order_by(*_ORDER)
            )
            if opportunity.study_year and study_year in opportunity.study_year
        ]
        total = len(matches)
        start = (page - 1) * page_size
        items = matches[start : start + page_size]

    return PaginatedOpportunityResponse(items=items, page=page, page_size=page_size, total=total)


@lru_cache
def _build_ai_scorer(url: str, model: str) -> AIScorer:
    return AIScorer(OllamaEmbedder(url, model))


def get_ai_scorer() -> AIScorer | None:
    """AI component for matching; ``None`` when Ollama is not configured."""
    settings = get_settings()
    if not settings.ollama_url:
        return None
    return _build_ai_scorer(settings.ollama_url, settings.ollama_embed_model)


def _get_opportunity_or_404(db: Session, opportunity_id: UUID) -> Opportunity:
    opportunity = db.scalar(
        select(Opportunity)
        .where(Opportunity.id == opportunity_id)
        .options(selectinload(Opportunity.skills))
    )
    if opportunity is None:
        raise APIError(
            "Opportunity not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
        )
    return opportunity


def _to_student_input(profile: Profile) -> StudentInput:
    # study_year is not part of the profile schema yet; it stays unknown.
    return StudentInput(
        degree_level=profile.degree_level,
        graduation_year=profile.graduation_year,
        location=profile.location,
    )


def _to_matching_profile(user: User) -> MatchingProfile:
    profile = user.profile
    return MatchingProfile(
        degree_level=profile.degree_level,
        graduation_year=profile.graduation_year,
        location=profile.location,
        field_of_study=profile.field_of_study,
        skills=[skill.name for skill in user.skills],
    )


def _to_matching_opportunity(opportunity: Opportunity) -> MatchingOpportunity:
    return MatchingOpportunity(
        title=opportunity.title,
        description=opportunity.description,
        location=opportunity.location,
        degree_level=opportunity.degree_level,
        study_year=opportunity.study_year,
        skills=[skill.name for skill in opportunity.skills],
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(db: Db, opportunity_id: UUID) -> Opportunity:
    return _get_opportunity_or_404(db, opportunity_id)


@router.get("/{opportunity_id}/eligibility", response_model=EligibilityResult)
def get_opportunity_eligibility(
    db: Db,
    opportunity_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
) -> EligibilityResult:
    """A9 full eligibility assessment for the current user's profile."""
    opportunity = _get_opportunity_or_404(db, opportunity_id)
    return evaluate_eligibility(
        _to_student_input(user.profile),
        to_opportunity_input(_to_matching_opportunity(opportunity)),
    )


@router.get("/{opportunity_id}/match", response_model=MatchResult)
def get_opportunity_match(
    db: Db,
    opportunity_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    ai: Annotated[AIScorer | None, Depends(get_ai_scorer)],
) -> MatchResult:
    """Explainable match score (A10 core + optional A11/A12 AI component)."""
    opportunity = _get_opportunity_or_404(db, opportunity_id)
    return score_match(
        _to_matching_profile(user),
        _to_matching_opportunity(opportunity),
        ai=ai,
    )
