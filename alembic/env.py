"""Alembic environment configuration for 小布的旅行.

Reads DATABASE_URL from the project's config (which loads from .env or defaults).
Supports both online (direct DB connection) and offline (SQL script) migrations.
"""

import os
import sys
from logging.config import fileConfig

# Ensure the project root is on sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from alembic import context
from sqlalchemy import engine_from_config, pool, create_engine

# Import project config and models
from config import settings
from models import Base

# Alembic Config object
config = context.config

# Set sqlalchemy.url from our project settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL to stdout (or a script) without connecting to a database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    """
    url = config.get_main_option("sqlalchemy.url")

    if url.startswith("sqlite"):
        connectable = create_engine(url, connect_args={"check_same_thread": False})
    else:
        connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
