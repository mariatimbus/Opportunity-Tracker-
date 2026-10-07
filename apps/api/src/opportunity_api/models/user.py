"""User model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ..core.database import Base

if TYPE_CHECKING:
    from .application import Application
    from .profile import Profile
    from .skill import Skill


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
    updated_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=sa.func.now(),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: orm.Mapped[uuid.UUID] = orm.mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    email: orm.Mapped[str] = orm.mapped_column(sa.String(255), unique=True, index=True)
    password_hash: orm.Mapped[str] = orm.mapped_column(sa.String(255))
    full_name: orm.Mapped[str] = orm.mapped_column(sa.String(255))
    is_active: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, default=True)

    profile: orm.Mapped["Profile"] = orm.relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    skills: orm.Mapped[list["Skill"]] = orm.relationship(
        secondary="user_skills", back_populates="users"
    )
    applications: orm.Mapped[list["Application"]] = orm.relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
