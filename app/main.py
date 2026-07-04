"""
FastAPI application entry point.

This module creates and configures the FastAPI app instance. It is the file
Uvicorn imports when starting the server:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Everything that needs to happen at startup (logging, directory creation,
database connection checks) is registered here via lifespan events.
"""

import logging
from contextlib import asynccontextmanager

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging import setup_logging

# Set up logging FIRST — before any other imports that might log something.
# If logging is configured after other modules run, early log messages are lost.
setup_logging()

logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown logic for the FastAPI application.

    Everything BEFORE `yield` runs at startup.
    Everything AFTER `yield` runs at shutdown.

    This replaces the older @app.on_event("startup") pattern, which is
    deprecated in FastAPI 0.93+. The lifespan approach is cleaner because
    startup and shutdown logic live in one place.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info(
        "Starting Transaction Processing API",
        extra={"environment": settings.app_env, "log_level": settings.log_level},
    )

    # Create the uploads directory if it doesn't exist.
    # When the container starts fresh, /app/uploads won't exist yet.
    # os.makedirs with exist_ok=True is safe to call even if the dir exists —
    # it won't raise an error or wipe existing files.
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info("Upload directory ready", extra={"path": settings.upload_dir})

    yield  # Application is now running and serving requests

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down Transaction Processing API")


# ── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    description=(
        "Accepts CSV uploads of financial transactions, processes them "
        "asynchronously through a job queue, uses an LLM to classify "
        "transactions and flag anomalies, and returns structured reports."
    ),
    version="1.0.0",
    # In production, disable the interactive docs to reduce attack surface.
    # Swagger UI at /docs and ReDoc at /redoc are useful in development.
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)


# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    # In production, replace "*" with your actual frontend domain.
    # "*" means any origin can call this API — fine for an assignment,
    # but a security risk in a real product.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

# We import the router here (not at the top of the file) to avoid circular
# imports. The jobs router imports from app.database, app.models, etc.
# Those modules in turn may import from app.config. Importing routers at
# the bottom of main.py ensures config is fully loaded before routes are
# registered.
from app.api.routes import jobs  # noqa: E402
from app.core.exceptions import register_exception_handlers 
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

register_exception_handlers(app)
# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    """
    Simple liveness probe.

    Docker Compose and container orchestration systems (Kubernetes, ECS) call
    this endpoint periodically to verify the application is running. If this
    returns a non-200 status, the container is considered unhealthy and may
    be restarted automatically.

    This endpoint intentionally does NOT check database or Redis connectivity —
    that would make it a "readiness probe" rather than a "liveness probe".
    We keep them separate: liveness = "is the process alive?",
    readiness = "is the process ready to serve traffic?".
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "environment": settings.app_env,
            "version": "1.0.0",
        }
    )