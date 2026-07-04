"""
Application configuration.

All settings are loaded from environment variables (or a .env file when running
locally). Pydantic-Settings validates every value at startup, so the application
fails immediately — with a clear error — if a required variable is missing or
has the wrong type.

Import the `settings` singleton anywhere in the codebase:
    from app.config import settings
    print(settings.postgres_host)
"""

from functools import lru_cache
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration values for the application.

    Pydantic-Settings automatically reads each attribute from the matching
    environment variable (case-insensitive). For example, the attribute
    `postgres_user` is populated from the environment variable `POSTGRES_USER`.
    """

    # ── Model config ──────────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",           # Load from .env file when running locally
        env_file_encoding="utf-8", # Always use UTF-8 to read the .env file
        case_sensitive=False,      # POSTGRES_HOST and postgres_host both work
        extra="ignore",            # Silently ignore unknown env vars
    )

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    postgres_user: str = Field(..., description="PostgreSQL username")
    postgres_password: str = Field(..., description="PostgreSQL password")
    postgres_db: str = Field(..., description="PostgreSQL database name")
    postgres_host: str = Field(..., description="PostgreSQL host (service name in Docker)")
    postgres_port: int = Field(5432, description="PostgreSQL port")

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_host: str = Field(..., description="Redis host (service name in Docker)")
    redis_port: int = Field(6379, description="Redis port")

    # ── Celery ─────────────────────────────────────────────────────────────────
    celery_broker_url: str = Field(..., description="Redis URL for Celery broker")
    celery_result_backend: str = Field(..., description="Redis URL for Celery results")

    # ── LLM ────────────────────────────────────────────────────────────────────
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    gemini_model: str = Field("gemini-1.5-flash", description="Gemini model name")

    # ── Application ────────────────────────────────────────────────────────────
    app_env: str = Field("development", description="Environment: development | production")
    log_level: str = Field("INFO", description="Logging level")
    max_upload_size_bytes: int = Field(10_485_760, description="Max CSV upload size in bytes")
    upload_dir: str = Field("/app/uploads", description="Directory for uploaded CSV files")

    # ── Computed fields ────────────────────────────────────────────────────────
    @computed_field
    @property
    def database_url(self) -> str:
        """
        Assembles the full async database URL from individual components.

        Using asyncpg driver for async SQLAlchemy support.
        Format: postgresql+asyncpg://user:password@host:port/database
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def sync_database_url(self) -> str:
        """
        Synchronous database URL — used only by Alembic migrations.

        Alembic's migration runner is synchronous (it doesn't use async/await),
        so it needs a sync driver (psycopg2-style URL) rather than asyncpg.
        We achieve this by replacing '+asyncpg' with an empty string, falling
        back to SQLAlchemy's default sync driver.
        """
        return self.database_url.replace("+asyncpg", "")

    @property
    def is_production(self) -> bool:
        """Returns True when running in production environment."""
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns the Settings singleton.

    @lru_cache ensures this function runs only once no matter how many times
    it's called. The Settings object is created on first call and reused
    forever after. This means:
    - Environment variables are read exactly once at startup
    - All parts of the app share the same config object
    - No repeated disk I/O from re-reading the .env file

    Usage:
        from app.config import settings   ← use this everywhere
        from app.config import get_settings  ← use this in FastAPI Depends()
    """
    return Settings()


# Module-level singleton — import this directly everywhere in the codebase
settings: Settings = get_settings()      