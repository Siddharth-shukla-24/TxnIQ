"""
JobSummary model — the LLM-generated narrative report for a completed job.

One JobSummary is created per Job after the full pipeline completes.
It is a one-to-one relationship: each Job has at most one Summary.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.job import Job


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="FK to jobs.id — one summary per job",
    )

    total_spend_inr: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Sum of all INR transaction amounts",
    )

    total_spend_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Sum of all USD transaction amounts",
    )

    top_merchants: Mapped[Optional[list]] = mapped_column(
    JSON,
    nullable=True,
    comment="Top 3 merchants by spend [{merchant, total_spend}]",
)

    anomaly_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of transactions flagged as anomalies",
    )

    narrative: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="2-3 sentence LLM-generated spending narrative",
    )

    risk_level: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="LLM-assessed risk level: low | medium | high",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job: Mapped["Job"] = relationship("Job", back_populates="summary")

    def __repr__(self) -> str:
        return (
            f"<JobSummary job_id={self.job_id} "
            f"risk={self.risk_level} anomalies={self.anomaly_count}>"
        )