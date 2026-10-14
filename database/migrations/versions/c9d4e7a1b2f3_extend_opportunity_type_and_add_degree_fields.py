"""extend opportunity_type enum, add opportunity degree fields, add updated_at triggers

Revision ID: c9d4e7a1b2f3
Revises: b7e2f1a9c304
Create Date: 2026-10-14 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d4e7a1b2f3"
down_revision: str | None = "b7e2f1a9c304"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPDATED_AT_TABLES = ("opportunities", "skills", "users", "applications", "profiles")

_SET_UPDATED_AT_FUNCTION = """
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # New enum values must be committed before they can be used, so each
        # ALTER TYPE runs in its own implicit transaction statement.
        op.execute("ALTER TYPE opportunity_type ADD VALUE IF NOT EXISTS 'research'")
        op.execute("ALTER TYPE opportunity_type ADD VALUE IF NOT EXISTS 'conference'")
        op.execute("ALTER TYPE opportunity_type ADD VALUE IF NOT EXISTS 'summer_school'")

    with op.batch_alter_table("opportunities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("degree_level", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("study_year", sa.JSON(), nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute(_SET_UPDATED_AT_FUNCTION)
        for table in UPDATED_AT_TABLES:
            op.execute(
                f"CREATE TRIGGER {table}_set_updated_at "
                f"BEFORE UPDATE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in UPDATED_AT_TABLES:
            op.execute(f"DROP TRIGGER IF EXISTS {table}_set_updated_at ON {table}")
        op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    with op.batch_alter_table("opportunities", schema=None) as batch_op:
        batch_op.drop_column("study_year")
        batch_op.drop_column("degree_level")

    # Enum values cannot be removed from a PostgreSQL enum type in place.
