"""Profile model — one-to-one with User."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from ..core.database import Base
from .user import TimestampMixin

if TYPE_CHECKING:
    from .user import User


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: orm.Mapped[uuid.UUID] = orm.mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    user_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    headline: orm.Mapped[str | None] = orm.mapped_column(sa.String(255), nullable=True)
    bio: orm.Mapped[str | None] = orm.mapped_column(sa.Text, nullable=True)
    location: orm.Mapped[str | None] = orm.mapped_column(sa.String(255), nullable=True)
    resume_url: orm.Mapped[str | None] = orm.mapped_column(sa.String(512), nullable=True)

    user: orm.Mapped["User"] = orm.relationship(back_populates="profile")
