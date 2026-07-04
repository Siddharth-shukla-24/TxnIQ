"""
Celery task: full transaction processing pipeline.

Orchestrates all service modules in sequence:
  a) Data cleaning        → services/cleaning.py
  b) Anomaly detection    → services/anomaly.py
  c) LLM classification   → services/llm_client.py
  d) Narrative summary    → services/llm_client.py
  e) Persist to DB        → SQLAlchemy sync session
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.workers.celery_app import celery_app
from app.models.job import Job
from app.models.transaction import Transaction
from app.models.job_summary import JobSummary
from app.services.cleaning import run_cleaning_pipeline
from app.services.anomaly import run_anomaly_detection
from app.services.llm_client import classify_transactions, generate_narrative_summary, compute_fallback_summary

logger = logging.getLogger(__name__)

# Synchronous engine for the Celery worker.
# We cannot use the async engine from database.py here because
# Celery tasks run in a synchronous context.
_sync_engine = create_engine(
    settings.sync_database_url,
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
)
_SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)


def _get_sync_db() -> Session:
    """Returns a new synchronous database session."""
    return _SyncSession()


@celery_app.task(
    name="app.workers.tasks.process_job",
    max_retries=0,
    time_limit=600,
    soft_time_limit=540,
)
def process_job(job_id: str) -> dict:
    """
    Full pipeline: clean → detect anomalies → LLM classify → summarize → persist.
    """
    logger.info("Pipeline starting", extra={"job_id": job_id})

    db: Session = _get_sync_db()

    try:
        # ── Load job ──────────────────────────────────────────────────────────
        job = db.get(Job, uuid.UUID(job_id))
        if not job:
            logger.error("Job not found — skipping", extra={"job_id": job_id})
            return {"job_id": job_id, "status": "failed"}

        # ── Idempotency guard ─────────────────────────────────────────────────
        # Protects against two failure modes:
        #   1. Celery retries a task that already succeeded (network blip)
        #   2. Duplicate messages in Redis (rare but possible under high load)
        # Without this guard, re-running inserts duplicate Transaction rows,
        # violating data integrity even though there's no DB unique constraint.
        if job.status == "completed":
            logger.warning(
                "Job already completed — skipping duplicate task",
                extra={"job_id": job_id},
            )
            return {"job_id": job_id, "status": "completed"}

        if job.status == "failed":
            logger.warning(
                "Job previously failed — skipping duplicate task",
                extra={"job_id": job_id},
            )
            return {"job_id": job_id, "status": "failed"}

        if job.status == "processing":
            logger.warning(
                "Job already processing — possible duplicate worker execution",
                extra={"job_id": job_id},
            )
            # Don't return here — previous worker may have crashed mid-task.
            # Allow re-processing but log the anomaly for investigation.
            # In production you'd use a distributed lock (Redis SETNX) here.

        # ── Mark as processing ────────────────────────────────────────────────
        job.status = "processing"
        db.commit()

        # ── Read uploaded CSV from disk ────────────────────────────────────────
        csv_path = os.path.join(settings.upload_dir, f"{job_id}.csv")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"CSV file not found at {csv_path}. "
                f"File may have been deleted or volume mount is incorrect."
            )

        with open(csv_path, "rb") as f:
            csv_bytes = f.read()

        # ── Step (a): Clean ───────────────────────────────────────────────────
        cleaned_df, row_count_raw, row_count_clean = run_cleaning_pipeline(csv_bytes)
        job.row_count_raw = row_count_raw
        job.row_count_clean = row_count_clean
        db.commit()

        # ── Step (b): Anomaly detection ───────────────────────────────────────
        cleaned_df = run_anomaly_detection(cleaned_df)

        # ── Step (c): LLM classification ──────────────────────────────────────
        all_rows = cleaned_df.to_dict(orient="records")
        uncategorised = [
            r for r in all_rows
            if str(r.get("category", "")).strip().lower() == "uncategorised"
        ]

        if uncategorised:
            classified = classify_transactions(uncategorised)
            llm_map = {r["txn_id"]: r for r in classified}
            for row in all_rows:
                if row["txn_id"] in llm_map:
                    row.update({
                        "llm_category": llm_map[row["txn_id"]].get("llm_category"),
                        "llm_raw_response": llm_map[row["txn_id"]].get("llm_raw_response"),
                        "llm_failed": llm_map[row["txn_id"]].get("llm_failed", False),
                    })
                    if row.get("llm_category") and not row.get("llm_failed"):
                        row["category"] = row["llm_category"]

        # ── Step (d): Narrative summary ───────────────────────────────────────
        summary_data = generate_narrative_summary(all_rows)
        if summary_data is None:
            logger.warning(
                "LLM summary failed — using computed fallback",
                extra={"job_id": job_id},
            )
            summary_data = compute_fallback_summary(all_rows)

        # ── Step (e): Persist transactions ────────────────────────────────────
        transaction_objects = [
            Transaction(
                job_id=uuid.UUID(job_id),
                txn_id=row.get("txn_id"),
                date=row.get("date"),
                merchant=row.get("merchant"),
                amount=row.get("amount"),
                currency=row.get("currency"),
                txn_status=row.get("status"),
                category=row.get("category"),
                account_id=row.get("account_id"),
                notes=row.get("notes"),
                is_anomaly=bool(row.get("is_anomaly", False)),
                anomaly_reason=row.get("anomaly_reason"),
                llm_category=row.get("llm_category"),
                llm_raw_response=row.get("llm_raw_response"),
                llm_failed=bool(row.get("llm_failed", False)),
            )
            for row in all_rows
        ]

        # add_all replaces deprecated bulk_save_objects (fixes M2 simultaneously)
        db.add_all(transaction_objects)

        # ── Persist summary ───────────────────────────────────────────────────
        summary = JobSummary(
            job_id=uuid.UUID(job_id),
            total_spend_inr=summary_data.get("total_spend_inr"),
            total_spend_usd=summary_data.get("total_spend_usd"),
            top_merchants=summary_data.get("top_merchants"),
            anomaly_count=summary_data.get("anomaly_count", 0),
            narrative=summary_data.get("narrative"),
            risk_level=summary_data.get("risk_level"),
        )
        db.add(summary)

        # ── Mark completed ────────────────────────────────────────────────────
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Pipeline complete",
            extra={"job_id": job_id, "rows": row_count_clean},
        )
        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        logger.error(
            "Pipeline failed",
            extra={"job_id": job_id, "error": str(e)},
            exc_info=True,
        )
        try:
            job = db.get(Job, uuid.UUID(job_id))
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as inner_e:
            logger.error(
                "Failed to update job status after pipeline failure",
                extra={"job_id": job_id, "error": str(inner_e)},
            )
        raise

    finally:
        db.close()