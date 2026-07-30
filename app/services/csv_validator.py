"""
CSV upload validation.

Validates files synchronously in the API layer before queuing.
Fast failures here save worker resources and give users instant feedback.
"""

import io
import logging
from fastapi import UploadFile, HTTPException
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)

# Every valid CSV from this system must have these exact columns.
# Checked case-insensitively after stripping whitespace.
REQUIRED_COLUMNS = {
    "txn_id", "date", "merchant", "amount",
    "currency", "status", "category", "account_id", "notes"
}


async def validate_csv(file: UploadFile) -> bytes:
    """
    Validates an uploaded CSV file.

    Checks:
      1. File extension is .csv
      2. File size is within MAX_UPLOAD_SIZE_BYTES
      3. File is parseable as CSV
      4. All required columns are present

    Returns:
        The raw file contents as bytes (already read, ready to save to disk).

    Raises:
        HTTPException 400 with a descriptive message on any validation failure.

    Why return bytes?
        UploadFile is a stream — once read, it's exhausted.
        We read it once here for validation and return the bytes
        so the caller doesn't need to read the stream again.
    """

    # ── 1. Extension check ────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected a .csv file, got: {file.filename!r}",
        )

    # ── 2. Read file into memory ──────────────────────────────────────────────
    contents = await file.read()

    # ── 3. Size check ─────────────────────────────────────────────────────────
    size = len(contents)
    if size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if size > settings.max_upload_size_bytes:
        limit_mb = settings.max_upload_size_bytes / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {actual_mb:.1f}MB. Limit is {limit_mb:.0f}MB.",
        )

    # ── 4. Parse check ────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(io.BytesIO(contents), nrows=1)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"File could not be parsed as CSV: {str(e)}",
        )

    # ── 5. Column check ───────────────────────────────────────────────────────
    actual_columns = {col.strip().lower() for col in df.columns}
    missing = REQUIRED_COLUMNS - actual_columns
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_CSV_SCHEMA",
                "title": "Invalid CSV Format",
                "description": (
                    "The uploaded file doesn't match the required "
                    "TxnIQ transaction schema."
                ),
                "required_columns": sorted(REQUIRED_COLUMNS),
                "missing_columns": sorted(missing),
            },
        )

    logger.info(
        "CSV validation passed",
        extra={"uploaded_filename": file.filename, "size_bytes": size},
    )
    return contents