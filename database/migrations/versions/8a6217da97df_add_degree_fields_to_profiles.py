"""add degree fields to profiles

Revision ID: 8a6217da97df
Revises: 5ec54ca754a9
Create Date: 2026-10-07 18:23:02.481227

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a6217da97df"
down_revision: str | None = "5ec54ca754a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "degree_level", sa.Enum("bachelor", "master", name="degree_level"), nullable=True
            )
        )
        batch_op.add_column(sa.Column("field_of_study", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("university", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("graduation_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("profiles", schema=None) as batch_op:
        batch_op.drop_column("graduation_year")
        batch_op.drop_column("university")
        batch_op.drop_column("field_of_study")
        batch_op.drop_column("degree_level")
