"""
Transaction model — one cleaned row from the uploaded CSV.

Each transaction belongs to exactly one Job. After the cleaning pipeline runs,
one Transaction row is inserted per valid CSV row (duplicates removed).

The LLM classification results and anomaly detection flags are stored here
alongside the cleaned transaction data.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.job import Job


class Transaction(Base):
    """
    One cleaned, enriched transaction row from a CSV upload.

    Table name: transactions
    """

    __tablename__ = "transactions"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Key ───────────────────────────────────────────────────────────
    # Links this transaction to its parent Job.
    # ondelete="CASCADE" is the DATABASE-level cascade — if the Job row is
    # deleted directly via SQL (bypassing SQLAlchemy), PostgreSQL also deletes
    # the transactions. This complements the SQLAlchemy-level cascade in Job.
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # We frequently query "all transactions for job X" — index helps
    )

    # ── Original CSV fields (cleaned) ─────────────────────────────────────────
    # txn_id is nullable because some rows in the CSV have blank txn_id.
    # We generate a surrogate UUID for internal tracking (the `id` column),
    # but store the original txn_id here for reference and deduplication.
    txn_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Original transaction ID from CSV. Null if the CSV row had none.",
    )

    # Date after normalization to ISO 8601 (YYYY-MM-DD).
    # Stored as SQL Date type (not DateTime) since the CSV has no time component.
    date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Transaction date, normalized to ISO 8601",
    )

    merchant: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,  # Queried in top-merchants aggregation
    )

    # Numeric(12, 2): up to 12 digits total, 2 after decimal point.
    # Max value: 9,999,999,999.99 — sufficient for any realistic transaction amount.
    # Why Numeric instead of Float?
    # Float is approximate (binary floating point). 0.1 + 0.2 = 0.30000000000000004.
    # Numeric is exact (decimal arithmetic). 0.1 + 0.2 = 0.3.
    # For money, exact arithmetic is non-negotiable.
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Transaction amount, cleaned ($ prefix removed, normalized)",
    )

    currency: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO currency code: INR or USD (uppercased during cleaning)",
    )

    # The transaction status from the CSV (SUCCESS/FAILED/PENDING), uppercased.
    # Named txn_status to avoid shadowing SQLAlchemy internals.
    txn_status: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Transaction status: SUCCESS | FAILED | PENDING",
    )

    # Spending category. May come from the CSV or be assigned by the LLM.
    # Rows with no category get 'Uncategorised' during cleaning, then the LLM
    # may replace 'Uncategorised' with a specific category.
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,  # Queried for per-category spend breakdown
        comment="Spending category, from CSV or LLM-assigned",
    )

    account_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,  # Used for per-account median calculation in anomaly detection
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text notes from CSV (SUSPICIOUS, Duplicate?, Verified, etc.)",
    )

    # ── Anomaly Detection flags ────────────────────────────────────────────────
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,  # Queried to get all anomalous transactions
        comment="True if this transaction was flagged by anomaly detection",
    )

    anomaly_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Human-readable reason for anomaly flag. "
            "E.g.: 'Amount 15000 exceeds 3x account median 3000' or "
            "'USD transaction with domestic-only merchant IRCTC'"
        ),
    )

    # ── LLM Classification results ─────────────────────────────────────────────
    # llm_category: the category assigned by the LLM (may differ from `category`
    # if the LLM overrides an existing one — but per spec, LLM only classifies
    # rows where category was blank/Uncategorised).
    llm_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Category assigned by the LLM for previously uncategorised transactions",
    )

    # The raw JSON response from the LLM — stored for debugging and auditability.
    # If something goes wrong with LLM classification, you can inspect exactly
    # what the model returned.
    llm_raw_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Raw LLM response text, stored for debugging",
    )

    # True if all LLM retry attempts for this transaction's batch failed.
    llm_failed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if LLM classification failed after all retries",
    )

    # ── Relationship back to Job ───────────────────────────────────────────────
    job: Mapped["Job"] = relationship("Job", back_populates="transactions")

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} merchant={self.merchant} "
            f"amount={self.amount} {self.currency} anomaly={self.is_anomaly}>"
        )