"""
Job API routes.

POST /jobs/upload           → validate CSV, create Job, queue processing
GET  /jobs/{job_id}/status  → poll job state
GET  /jobs/{job_id}/results → full structured output
GET  /jobs                  → list all jobs with optional ?status= filter
GET  /jobs/sample-csv       → download a sample CSV template
"""

import asyncio
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.job import Job
from app.models.transaction import Transaction
from app.models.job_summary import JobSummary
from app.schemas.job import (
    JobUploadResponse,
    JobStatusResponse,
    JobSummarySchema,
    JobListResponse,
    JobListItem,
)
from app.schemas.transaction import JobResultsResponse, TransactionSchema, CategoryBreakdown
from app.services.csv_validator import validate_csv, REQUIRED_COLUMNS
from app.workers.tasks import process_job
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helper: non-blocking file write ───────────────────────────────────────────

def _write_file(path: str, contents: bytes) -> None:
    """
    Synchronous file write.

    This function is intentionally synchronous because it is called via
    run_in_executor() which moves it to a thread pool. Defining it as a
    named function (instead of a lambda) gives cleaner tracebacks when
    errors occur during the write.

    Never call this directly from an async route handler — always use
    await loop.run_in_executor(None, _write_file, path, contents).
    """
    with open(path, "wb") as f:
        f.write(contents)


# ── GET /jobs/sample-csv ──────────────────────────────────────────────────────

# Sample rows that demonstrate the expected CSV schema.
# Intentionally small — just enough for users to understand the format.
_SAMPLE_CSV = (
    "txn_id,date,merchant,amount,currency,status,category,account_id,notes\n"
    "TXN0001,2024-01-15,Amazon,2499.99,INR,SUCCESS,Shopping,ACC001,Gift purchase\n"
    "TXN0002,2024-01-16,Swiggy,450.00,INR,SUCCESS,Food,ACC002,\n"
    "TXN0003,2024-01-17,Ola,189.50,INR,FAILED,Transport,ACC001,Refund expected\n"
)


@router.get("/sample-csv", tags=["jobs"])
async def download_sample_csv():
    """
    Returns a minimal sample CSV file that demonstrates the required schema.

    Useful for users who receive an "Invalid CSV Format" error and need a
    quick reference for the expected column layout.
    """
    return StreamingResponse(
        iter([_SAMPLE_CSV]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="txniq_sample.csv"'
        },
    )


# ── POST /jobs/upload ─────────────────────────────────────────────────────────

@router.post("/upload", response_model=JobUploadResponse, status_code=202)
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a CSV upload, validate it, create a Job record, queue processing.

    Returns 202 Accepted immediately — processing is asynchronous.
    Use GET /jobs/{job_id}/status to poll for completion.

    Operation order is critical for correctness:

        Step 1 — Validate:
            Reject bad files immediately. No DB writes, no disk writes.
            User gets instant 400 feedback instead of waiting for worker failure.

        Step 2 — Commit Job to DB:
            The Job row must exist in PostgreSQL and be COMMITTED (not just
            flushed) before the worker starts. A flushed-but-uncommitted row
            is invisible to other database connections. If we enqueue before
            commit, the worker calls db.get(Job, id) and gets None.

        Step 3 — Write CSV to disk (non-blocking):
            File write is a synchronous OS call. Calling it directly in an
            async function freezes the entire event loop — no other requests
            are handled until the write completes. run_in_executor() moves
            the write to a thread pool so the event loop stays responsive.

        Step 4 — Enqueue Celery task:
            Only after Job is committed AND file is on disk. The worker needs
            both: the Job record to update status, the CSV file to process.
    """

    # ── Step 1: Validate ──────────────────────────────────────────────────────
    # validate_csv() reads the file stream and returns raw bytes.
    # It raises HTTPException 400 on: wrong extension, empty file,
    # file too large, unparseable CSV, missing required columns.
    # The upload stream is exhausted after this call — we use the
    # returned bytes for all subsequent operations.
    csv_bytes = await validate_csv(file)

    # ── Step 2: Create and COMMIT job record ──────────────────────────────────
    # Generate the UUID in Python, not the database.
    # We need the ID now to name the CSV file and to pass to the Celery task.
    # If we let PostgreSQL generate it, we'd need an extra round trip to
    # retrieve it after the insert.
    job_id = uuid.uuid4()

    job = Job(
        id=job_id,
        filename=file.filename,
        status="pending",
        # row_count_raw and row_count_clean are NULL here.
        # The worker fills them in after parsing the CSV.
    )
    db.add(job)

    # commit() flushes AND makes the transaction permanent.
    # After this line, the Job row is visible to all database connections,
    # including the separate PostgreSQL connection the Celery worker uses.
    await db.commit()

    logger.info(
        "Job record committed",
        extra={"job_id": str(job_id), "uploaded_filename": file.filename},
    )

    # ── Step 3: Write CSV to disk — NON-BLOCKING ──────────────────────────────
    # Why not just open() and write() directly?
    #
    # FastAPI's async event loop is single-threaded. When you call a
    # synchronous blocking function inside an async route handler, Python
    # does not switch to another coroutine while waiting — it freezes.
    # For a 10MB file, this blocks ALL other requests for 100-500ms.
    #
    # run_in_executor(None, fn, *args):
    #   - None = use the default ThreadPoolExecutor (managed by asyncio)
    #   - Runs fn(*args) in a worker thread
    #   - Returns a coroutine that completes when the thread finishes
    #   - The event loop is FREE to handle other requests during the write
    #
    # We name the file by job_id (a UUID) — no two uploads can collide.
    os.makedirs(settings.upload_dir, exist_ok=True)
    csv_path = os.path.join(settings.upload_dir, f"{job_id}.csv")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _write_file,  # function to run in thread pool
        csv_path,     # first argument to _write_file
        csv_bytes,    # second argument to _write_file
    )

    logger.info(
        "CSV written to disk",
        extra={"job_id": str(job_id), "path": csv_path, "bytes": len(csv_bytes)},
    )

    # ── Step 4: Enqueue Celery task ───────────────────────────────────────────
    # .delay(job_id) is shorthand for .apply_async(args=[job_id]).
    # It serializes the call to JSON: {"task": "process_job", "args": ["<uuid>"]}
    # and sends it to Redis (the Celery broker).
    # This call returns immediately — it does NOT wait for the task to run.
    #
    # We pass job_id as a string, not a UUID object, because Celery
    # serializes arguments as JSON. UUID is not JSON-serializable by default.
    # The worker receives the string and converts it back: uuid.UUID(job_id).
    process_job.delay(str(job_id))

    logger.info(
        "Job enqueued",
        extra={"job_id": str(job_id)},
    )

    return JobUploadResponse(
        job_id=job_id,
        status="pending",
        message=(
            f"Job queued successfully. "
            f"Poll GET /jobs/{job_id}/status for updates."
        ),
    )


# ── GET /jobs/{job_id}/status ─────────────────────────────────────────────────

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns current job status.
    When status is 'completed', also returns high-level summary stats.
    """
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.summary))
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found.",
        )

    summary_schema = None
    if job.status == "completed" and job.summary:
        summary_schema = JobSummarySchema.model_validate(job.summary)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        filename=job.filename,
        row_count_raw=job.row_count_raw,
        row_count_clean=job.row_count_clean,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        summary=summary_schema,
    )


# ── GET /jobs/{job_id}/results ────────────────────────────────────────────────

@router.get("/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full structured output: cleaned transactions, flagged anomalies,
    per-category spend breakdown, and LLM narrative summary.

    Only available when job status is 'completed'.
    Returns 409 Conflict if job is still processing.
    """
    result = await db.execute(
        select(Job)
        .options(
            selectinload(Job.transactions),
            selectinload(Job.summary),
        )
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found.",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Results are not available yet. "
                f"Current status: '{job.status}'. "
                f"Poll GET /jobs/{job_id}/status until status is 'completed'."
            ),
        )

    transactions = [TransactionSchema.model_validate(t) for t in job.transactions]
    anomalies = [t for t in transactions if t.is_anomaly]
    category_breakdown = _compute_category_breakdown(job.transactions)

    summary_schema = None
    if job.summary:
        summary_schema = JobSummarySchema.model_validate(job.summary)

    return JobResultsResponse(
        job_id=job.id,
        status=job.status,
        transactions=transactions,
        anomalies=anomalies,
        category_breakdown=category_breakdown,
        summary=summary_schema,
    )


# ── GET /jobs ─────────────────────────────────────────────────────────────────

@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter: pending|processing|completed|failed"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all jobs ordered by creation time (newest first).
    Supports ?status= query parameter for filtering.
    """
    valid_statuses = {"pending", "processing", "completed", "failed"}

    if status and status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {sorted(valid_statuses)}",
        )

    query = select(Job).order_by(Job.created_at.desc())
    if status:
        query = query.where(Job.status == status)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        total=len(jobs),
        jobs=[
            JobListItem(
                job_id=j.id,
                status=j.status,
                filename=j.filename,
                row_count_raw=j.row_count_raw,
                created_at=j.created_at,
            )
            for j in jobs
        ],
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _compute_category_breakdown(transactions) -> list[CategoryBreakdown]:
    """
    Computes per-category, per-currency spend totals.

    Groups by (category, currency) because INR and USD totals are
    meaningfully different — summing them together would require a
    conversion rate we don't have.

    Takes ORM Transaction objects (not dicts) — called after selectinload
    has already fetched all transactions.
    """
    from collections import defaultdict
    from decimal import Decimal

    # Key: (category_name, currency_code)
    # Value: {"total": Decimal, "count": int}
    groups: dict = defaultdict(lambda: {"total": Decimal("0"), "count": 0})

    for txn in transactions:
        if txn.amount is None:
            continue
        key = (
            txn.category or "Uncategorised",
            txn.currency or "UNKNOWN",
        )
        groups[key]["total"] += txn.amount
        groups[key]["count"] += 1

    return [
        CategoryBreakdown(
            category=category,
            total_amount=data["total"],
            transaction_count=data["count"],
            currency=currency,
        )
        for (category, currency), data in sorted(groups.items())
    ]