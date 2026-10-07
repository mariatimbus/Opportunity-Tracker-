"""Alembic environment.

Run migrations with the apps/api environment:

    cd apps/api
    DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/db \
        uv run alembic -c ../../database/migrations/alembic.ini upgrade head

DATABASE_URL is read from the environment; it falls back to a local sqlite
file so `alembic upgrade head` works as a smoke test without Postgres.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the api package importable when running from apps/api.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api" / "src"))

from opportunity_api import models  # noqa: E402, F401  (register all tables)
from opportunity_api.core.database import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url", os.environ.get("DATABASE_URL", "sqlite:///./opportunity_tracker.db")
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
