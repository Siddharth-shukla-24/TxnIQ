"""
Job model — represents one CSV upload and its processing state.

One Job record is created per CSV upload. Its `status` field transitions:
    pending → processing → completed
                        ↘ failed

The Job is the parent record. Transactions and JobSummary are children.
Deleting a Job cascades to delete all its Transactions and Summary.
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# TYPE_CHECKING is False at runtime — these imports only exist for type checkers.
# This avoids circular imports: Job imports Transaction type hint,
# Transaction imports Job type hint. At runtime neither actually imports the other.
if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.job_summary import JobSummary


class Job(Base):
    """
    Represents one CSV upload job and its lifecycle.

    Table name: jobs
    """

    __tablename__ = "jobs"

    # ── Primary Key ───────────────────────────────────────────────────────────
    # UUID instead of an auto-incrementing integer.
    # Why UUID?
    #   - IDs are unpredictable — a user can't guess job IDs of other users.
    #   - Safe to generate in Python before the DB insert (no round trip needed).
    #   - Works correctly when sharding across multiple databases.
    # UUID(as_uuid=True) stores as native PostgreSQL UUID type (16 bytes),
    # not as a 36-character string (36 bytes) — more efficient.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,  # Python generates the UUID, not the database
        comment="Unique job identifier",
    )

    # ── Core fields ───────────────────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename of the uploaded CSV",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,  # We filter jobs by status frequently — index speeds this up
        comment="Job lifecycle state: pending | processing | completed | failed",
    )

    # ── Row counts ────────────────────────────────────────────────────────────
    # Nullable because these are only known after the worker processes the file.
    # At upload time (status=pending), we don't know the counts yet.
    row_count_raw: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of rows in the original CSV (before cleaning)",
    )

    row_count_clean: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of rows after deduplication and cleaning",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    # server_default=func.now() means PostgreSQL sets this, not Python.
    # Why PostgreSQL instead of Python? The DB clock is authoritative —
    # if you run multiple API instances, their system clocks might differ by
    # milliseconds. The DB clock is always consistent.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the job was created (set by PostgreSQL)",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job reached completed or failed state",
    )

    # ── Error handling ────────────────────────────────────────────────────────
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,  # Text = unlimited length. String(n) would truncate long errors.
        nullable=True,
        comment="Populated when status=failed. Contains the exception message.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # Relationships tell SQLAlchemy how tables are connected.
    # They don't create new columns — they use the foreign keys defined in
    # the child tables to load related objects.

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="job",
        # cascade="all, delete-orphan": if you delete a Job, SQLAlchemy
        # automatically deletes all its Transactions too.
        # Without cascade, you'd get a foreign key constraint error.
        cascade="all, delete-orphan",
        # lazy="select" (default): loads transactions only when accessed.
        # We could use lazy="joined" to always load with the job,
        # but for large transaction lists that wastes memory.
    )

    summary: Mapped[Optional["JobSummary"]] = relationship(
        "JobSummary",
        back_populates="job",
        # uselist=False: this is a one-to-one relationship.
        # Without uselist=False, SQLAlchemy would return a list even though
        # there's only ever one summary per job.
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation for debugging — appears in logs and REPL."""
        return f"<Job id={self.id} status={self.status} file={self.filename}>"