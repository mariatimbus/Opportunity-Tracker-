"""Application model (user tracking an opportunity) and status enum."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ..core.database import Base
from .user import TimestampMixin

if TYPE_CHECKING:
    from .opportunity import Opportunity
    from .user import User


class ApplicationStatus(enum.StrEnum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "opportunity_id", name="uq_application_user_opportunity"),
    )

    id: orm.Mapped[uuid.UUID] = orm.mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    user_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.Uuid, sa.ForeignKey("opportunities.id", ondelete="CASCADE"), index=True
    )
    status: orm.Mapped[ApplicationStatus] = orm.mapped_column(
        sa.Enum(ApplicationStatus, native_enum=True, name="application_status"),
        default=ApplicationStatus.saved,
    )
    notes: orm.Mapped[str | None] = orm.mapped_column(sa.Text, nullable=True)
    applied_at: orm.Mapped[datetime | None] = orm.mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    user: orm.Mapped["User"] = orm.relationship(back_populates="applications")
    opportunity: orm.Mapped["Opportunity"] = orm.relationship(back_populates="applications")
