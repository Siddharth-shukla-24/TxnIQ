"""
Alembic migration environment configuration.

This file is run by Alembic when executing any migration command.
It configures:
  - Where to find the database (URL from our settings)
  - What the target schema looks like (our SQLAlchemy models)
  - How to run migrations (online vs offline mode)
"""

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import our settings to get the database URL.
# This ensures no credentials are hardcoded in alembic.ini.
from app.config import settings

# Import all models so Base.metadata knows about every table.
# This import triggers app/models/__init__.py which imports Job,
# Transaction, and JobSummary — registering all three tables.
from app.models import Base  # noqa: F401 — import for side effect

logger = logging.getLogger(__name__)

# Alembic's Config object — wraps alembic.ini settings
config = context.config

# Set up Python logging from alembic.ini's [loggers] section.
# This makes Alembic's own log output follow our logging config.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# THE critical line: tell Alembic what the target schema looks like.
# When you run `alembic revision --autogenerate`, Alembic compares
# Base.metadata (what your models define) against the live database
# (what currently exists) and generates the diff as a migration script.
target_metadata = Base.metadata

# Inject the database URL from our settings.
# We use sync_database_url because Alembic uses a synchronous connection.
# (psycopg2 driver, not asyncpg)
config.set_main_option("sqlalchemy.url", settings.sync_database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without connecting to DB.

    Useful for generating migration scripts to review before applying,
    or for environments where you can't connect to the DB at migration time.
    Run with: alembic upgrade head --sql
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
    """
    Run migrations in 'online' mode — connects to DB and applies changes.

    This is what runs when you do `alembic upgrade head` normally.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # NullPool: don't use connection pooling for migrations.
        # Migrations run once at startup — no need to keep connections open.
        # Using a pool here can cause issues with PostgreSQL's lock behavior
        # during schema changes.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # compare_type=True: detect column type changes during autogenerate.
            # Without this, changing String(50) to String(100) is not detected.
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()
            logger.info("Migrations applied successfully")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()