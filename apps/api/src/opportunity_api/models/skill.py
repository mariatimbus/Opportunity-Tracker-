"""Skill model and user/opportunity association tables."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ..core.database import Base
from .user import TimestampMixin

if TYPE_CHECKING:
    from .opportunity import Opportunity
    from .user import User

user_skills = sa.Table(
    "user_skills",
    Base.metadata,
    sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    sa.Column(
        "skill_id", sa.Uuid, sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    ),
)

opportunity_skills = sa.Table(
    "opportunity_skills",
    Base.metadata,
    sa.Column(
        "opportunity_id",
        sa.Uuid,
        sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "skill_id", sa.Uuid, sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"

    id: orm.Mapped[uuid.UUID] = orm.mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(100), unique=True, index=True)

    users: orm.Mapped[list["User"]] = orm.relationship(
        secondary=user_skills, back_populates="skills"
    )
    opportunities: orm.Mapped[list["Opportunity"]] = orm.relationship(
        secondary=opportunity_skills, back_populates="skills"
    )
