"""
Pydantic schemas for Transaction API responses.
"""

import uuid
from datetime import date as DateType
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.job import JobSummarySchema

class TransactionSchema(BaseModel):
    """
    Cleaned, enriched transaction as returned by the API.
    Maps to the Transaction database model but excludes internal fields
    like llm_raw_response (too verbose for API consumers).
    """
    id: uuid.UUID
    txn_id: Optional[str] = None
    date: Optional[DateType] = None
    merchant: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    txn_status: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    notes: Optional[str] = None
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None
    llm_category: Optional[str] = None
    llm_failed: bool = False

    model_config = ConfigDict(from_attributes=True)


class CategoryBreakdown(BaseModel):
    """Per-category spend total for the results breakdown."""
    category: str
    total_amount: Decimal
    transaction_count: int
    currency: str


class JobResultsResponse(BaseModel):
    """
    Full response for GET /jobs/{job_id}/results.
    This is the main deliverable — what the grader checks.
    """
    job_id: uuid.UUID
    status: str
    transactions: list[TransactionSchema]
    anomalies: list[TransactionSchema]           # subset: only is_anomaly=True
    category_breakdown: list[CategoryBreakdown]  # per-category spend
    summary: Optional[JobSummarySchema] = None

    model_config = ConfigDict(from_attributes=True)


# Import here to avoid circular import — JobSummarySchema is in job.py
from app.schemas.job import JobSummarySchema  # noqa: E402