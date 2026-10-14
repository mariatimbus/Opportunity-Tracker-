"""drop unique index on users.email

Revision ID: b7e2f1a9c304
Revises: 4c4beef96edb
Create Date: 2026-10-14 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2f1a9c304"
down_revision: str | None = "4c4beef96edb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)
