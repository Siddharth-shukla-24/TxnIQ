"""
Database engine, session factory, and declarative base.

All models import `Base` from this module to register their table definitions.
FastAPI route handlers receive an `AsyncSession` via the `get_db` dependency.

Architecture note:
    Engine     → knows HOW to connect (URL, driver, pool settings)
    Session    → knows WHAT to do (tracks pending inserts/updates/deletes)
    Base       → knows WHICH tables exist (metadata registry for all models)
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


# ── Declarative Base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base class.

    Every model (Job, Transaction, JobSummary) inherits from this class.
    Inheritance registers the model's table definition onto `Base.metadata`.
    Alembic reads `Base.metadata` to know which tables to create/alter.

    Why DeclarativeBase instead of the older `declarative_base()` function?
    DeclarativeBase is the SQLAlchemy 2.0 style — it supports Python type hints
    (Mapped[str], Mapped[int]) which give you IDE autocomplete and type safety.
    The older style is still valid but lacks these benefits.
    """
    pass


# ── Async Engine ───────────────────────────────────────────────────────────────

engine = create_async_engine(
    # The connection URL assembled by config.py from individual env vars.
    # Format: postgresql+asyncpg://user:password@host:port/database
    # The +asyncpg part tells SQLAlchemy to use the asyncpg driver.
    url=settings.database_url,

    # Log every SQL statement SQLAlchemy generates.
    # Only enable in development — in production this floods your logs.
    echo=settings.app_env == "development",

    # Connection pool settings:
    # pool_size: number of connections kept open permanently.
    # max_overflow: additional connections allowed when pool is exhausted.
    # Total max connections = pool_size + max_overflow = 5 + 10 = 15
    # Keep this below PostgreSQL's max_connections (default: 100).
    pool_size=5,
    max_overflow=10,

    # Before using a connection from the pool, send a lightweight ping to
    # verify it's still alive. Without this, a connection that PostgreSQL
    # closed due to inactivity timeout would cause your query to fail.
    # pool_pre_ping adds a tiny overhead but prevents "connection closed" errors.
    pool_pre_ping=True,
)


# ── Session Factory ────────────────────────────────────────────────────────────

# async_sessionmaker is a factory that creates AsyncSession objects.
# We configure it once here and reuse it throughout the application.
AsyncSessionLocal = async_sessionmaker(
    # Which engine (and therefore which database) these sessions connect to.
    bind=engine,

    # The class to instantiate. AsyncSession supports async/await.
    class_=AsyncSession,

    # expire_on_commit=False means objects don't become "expired" (unusable)
    # after a commit. With expire_on_commit=True (the default), accessing an
    # attribute after session.commit() triggers another DB query to refresh it.
    # In async code this causes confusing "MissingGreenlet" errors.
    # Setting False means: once loaded, the data stays in memory as-is.
    expire_on_commit=False,
)


# ── FastAPI Dependency ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage in a route handler:
        from app.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        from fastapi import Depends

        @router.post("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Job))
            ...

    How it works:
        1. FastAPI calls this function before the route handler runs.
        2. `async with AsyncSessionLocal() as session` opens a session
           (borrows a connection from the pool).
        3. `yield session` gives the session to the route handler.
        4. After the route handler returns (or raises), execution resumes here.
        5. If no exception: the `async with` block commits automatically.
        6. If exception: the `async with` block rolls back automatically.
        7. The connection is returned to the pool.

    Why a generator (yield) instead of a regular function (return)?
        A regular function runs once and returns. A generator can pause (at yield),
        let something else run (the route handler), then resume. This is how
        FastAPI implements "setup → run handler → teardown" in one function.
        The pattern is called a "context manager as a dependency."
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # The `async with` block handles closing, but we log for visibility.
            logger.debug("Database session closed")