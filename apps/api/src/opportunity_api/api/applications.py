"""Application tracking endpoints (saved opportunities). 🔒 authenticated.

Ownership rule: every query is scoped to the current user; another user's
application is indistinguishable from a missing one (404, never 403) — this
mirrors the Supabase RLS policy on applications (defense in depth).
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..core.database import get_db
from ..core.errors import APIError
from ..models import Application, ApplicationStatus, Opportunity, User
from ..schemas import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
)
from .deps import get_current_user

router = APIRouter(prefix="/applications", tags=["applications"])

Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

ApplicationExistsError = APIError(
    "This opportunity is already being tracked",
    status_code=status.HTTP_409_CONFLICT,
    code="application_exists",
)


def _stamp_applied(application: Application, applied_at: datetime | None) -> None:
    """Fill applied_at when the entry is (or becomes) 'applied'.

    An explicitly provided applied_at always wins; otherwise the transition
    to 'applied' stamps the current time once.
    """
    if applied_at is not None:
        application.applied_at = applied_at
    elif application.status == ApplicationStatus.applied and application.applied_at is None:
        application.applied_at = datetime.now(UTC)


def _get_owned_application(db: Session, current_user: User, application_id: UUID) -> Application:
    application = db.scalar(
        select(Application)
        .where(Application.id == application_id, Application.user_id == current_user.id)
        .options(selectinload(Application.opportunity))
    )
    if application is None:
        raise APIError(
            "Application not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="application_not_found",
        )
    return application


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    db: Db,
    current_user: CurrentUser,
    application_status: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
) -> ApplicationListResponse:
    stmt = (
        select(Application)
        .where(Application.user_id == current_user.id)
        .options(selectinload(Application.opportunity))
        .order_by(Application.created_at.desc(), Application.id)
    )
    if application_status is not None:
        stmt = stmt.where(Application.status == application_status)
    applications = list(db.scalars(stmt))
    return ApplicationListResponse(items=applications, total=len(applications))


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    payload: ApplicationCreate,
    db: Db,
    current_user: CurrentUser,
) -> Application:
    opportunity = db.get(Opportunity, payload.opportunity_id)
    if opportunity is None:
        raise APIError(
            "Opportunity not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="opportunity_not_found",
        )
    existing = db.scalar(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.opportunity_id == payload.opportunity_id,
        )
    )
    if existing is not None:
        raise ApplicationExistsError

    application = Application(
        user_id=current_user.id,
        opportunity_id=payload.opportunity_id,
        status=payload.status,
        notes=payload.notes,
    )
    _stamp_applied(application, payload.applied_at)
    db.add(application)
    try:
        db.flush()
    except IntegrityError:
        # Concurrent save of the same opportunity by the same user.
        db.rollback()
        raise ApplicationExistsError from None
    application.opportunity = opportunity
    db.commit()
    return application


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    db: Db,
    current_user: CurrentUser,
) -> Application:
    application = _get_owned_application(db, current_user, application_id)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data:
        application.status = data["status"]
    if "notes" in data:
        application.notes = data["notes"]
    _stamp_applied(application, data.get("applied_at"))
    db.commit()
    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: UUID,
    db: Db,
    current_user: CurrentUser,
) -> Response:
    application = _get_owned_application(db, current_user, application_id)
    db.delete(application)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
