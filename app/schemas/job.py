"""
Pydantic schemas for Job API request/response serialization.

These are NOT database models — they define the JSON contract between
the API and its clients. FastAPI automatically validates requests against
these schemas and serializes responses using them.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ── Response: POST /jobs/upload ──────────────────────

class JobUploadResponse(BaseModel):
    """Returned immediately after a CSV is uploaded and queued."""
    job_id: uuid.UUID
    status: str
    message: str


# ── Response: GET /jobs/{job_id}/status ────────────────────

class JobSummarySchema(BaseModel):
    """
    High-level stats included in the status response when job is completed.
    Mirrors the JobSummary database model but only exposes safe fields.
    """
    total_spend_inr: Optional[Decimal] = None
    total_spend_usd: Optional[Decimal] = None
    anomaly_count: int = 0
    risk_level: Optional[str] = None
    narrative: Optional[str] = None
    top_merchants: Optional[list] = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    """
    Response for GET /jobs/{job_id}/status.
    `summary` is only populated when status == "completed".
    """
    job_id: uuid.UUID
    status: str
    filename: str
    row_count_raw: Optional[int] = None
    row_count_clean: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    summary: Optional[JobSummarySchema] = None

    # model_config tells Pydantic how to handle SQLAlchemy model instances.
    # from_attributes=True (called orm_mode in Pydantic v1) allows Pydantic
    # to read data from object attributes instead of only dict keys.
    # Without this, passing a SQLAlchemy Job object to this schema fails.
    model_config = ConfigDict(from_attributes=True)


# ── Response: GET /jobs ───────────────────────────────────────────────────────

class JobListItem(BaseModel):
    """One item in the GET /jobs list."""
    job_id: uuid.UUID
    status: str
    filename: str
    row_count_raw: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Response for GET /jobs with optional status filter."""
    total: int
    jobs: list[JobListItem]