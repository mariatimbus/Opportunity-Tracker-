"""Opportunity model and opportunity type enum."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from ..core.database import Base
from .user import TimestampMixin

if TYPE_CHECKING:
    from .application import Application
    from .skill import Skill


class OpportunityType(enum.StrEnum):
    """Final vocabulary (2026-10-14, Maria, option A) — single source of truth.

    Must stay in sync with supabase/migrations (opportunity_type enum),
    docs/api.md, and database/seeds. Do not add synonyms.
    """

    internship = "internship"
    job = "job"
    research = "research"
    scholarship = "scholarship"
    fellowship = "fellowship"
    hackathon = "hackathon"
    competition = "competition"
    early_career = "early_career"
    open_source = "open_source"
    grant = "grant"
    other = "other"


class OpportunityDegreeLevel(enum.StrEnum):
    """Eligible degree for an opportunity (seed `degree_level`).

    Separate from the profiles `degree_level` enum, which describes the
    student's own degree and has no `both` value.
    """

    bachelor = "bachelor"
    master = "master"
    both = "both"


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        sa.UniqueConstraint("source", "source_id", name="uq_opportunity_source_source_id"),
    )

    id: orm.Mapped[uuid.UUID] = orm.mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    title: orm.Mapped[str] = orm.mapped_column(sa.String(255))
    description: orm.Mapped[str | None] = orm.mapped_column(sa.Text, nullable=True)
    organization: orm.Mapped[str | None] = orm.mapped_column(sa.String(255), nullable=True)
    opportunity_type: orm.Mapped[OpportunityType] = orm.mapped_column(
        sa.Enum(OpportunityType, native_enum=True, name="opportunity_type")
    )
    location: orm.Mapped[str | None] = orm.mapped_column(sa.String(255), nullable=True)
    url: orm.Mapped[str] = orm.mapped_column(sa.String(512), unique=True)
    source: orm.Mapped[str] = orm.mapped_column(sa.String(100))
    source_id: orm.Mapped[str] = orm.mapped_column(sa.String(255))
    deadline: orm.Mapped[datetime | None] = orm.mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    posted_at: orm.Mapped[datetime | None] = orm.mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    is_active: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, default=True)
    degree_level: orm.Mapped[OpportunityDegreeLevel | None] = orm.mapped_column(
        sa.Enum(OpportunityDegreeLevel, native_enum=True, name="opportunity_degree_level"),
        nullable=True,
    )
    study_year: orm.Mapped[list[int] | None] = orm.mapped_column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )

    skills: orm.Mapped[list["Skill"]] = orm.relationship(
        secondary="opportunity_skills", back_populates="opportunities"
    )
    applications: orm.Mapped[list["Application"]] = orm.relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
