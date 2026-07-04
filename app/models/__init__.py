"""
Models package.

Importing this package registers all models onto Base.metadata.
This is required for Alembic to detect all tables during migration generation.

Any new model added to this package MUST be imported here.
Forgetting to add an import here means Alembic won't create that table.
This is one of the most common migration bugs in SQLAlchemy projects.
"""

from app.models.job import Job
from app.models.transaction import Transaction
from app.models.job_summary import JobSummary

# Re-export Base so other modules can do:
#   from app.models import Base
# instead of:
#   from app.database import Base
from app.database import Base

__all__ = ["Job", "Transaction", "JobSummary", "Base"]