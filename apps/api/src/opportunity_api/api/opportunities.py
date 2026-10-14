"""Opportunity catalog endpoints: paginated list with filters and detail by id."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..core.database import get_db
from ..core.errors import APIError
from ..models import Opportunity, OpportunityDegreeLevel, OpportunityType
from ..schemas import OpportunityResponse, PaginatedOpportunityResponse

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

    stmt = _apply_filters(select(Opportunity), **filters)
    if study_year is None:
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


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(db: Db, opportunity_id: UUID) -> Opportunity:
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
