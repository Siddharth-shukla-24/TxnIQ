"""
Data cleaning pipeline — Step (a) of the processing spec.

Input:  Raw CSV bytes
Output: Cleaned pandas DataFrame

Cleaning steps in order:
  1. Parse CSV
  2. Normalize date formats to ISO 8601
  3. Strip currency symbols from amounts, convert to float
  4. Uppercase status and currency
  5. Fill missing categories with 'Uncategorised'
  6. Remove exact duplicate rows
  7. Generate surrogate txn_id for rows that have none
"""

import io
import logging
import uuid
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> Optional[str]:
    """
    Parses a date string in either DD-MM-YYYY or YYYY/MM/DD format.
    Returns ISO 8601 string (YYYY-MM-DD) or None if unparseable.

    Why two formats?
    The CSV intentionally has mixed formats — this is the messy real-world
    data the spec refers to. We detect the format by the separator character:
      '-' separator → assume DD-MM-YYYY  (e.g., "15-03-2024")
      '/' separator → assume YYYY/MM/DD  (e.g., "2024/03/15")
    """
    if not date_str or pd.isna(date_str):
        return None

    date_str = str(date_str).strip()

    formats = [
        "%d-%m-%Y",   # DD-MM-YYYY  (dash separated, day first)
        "%Y/%m/%d",   # YYYY/MM/DD  (slash separated, year first)
        "%Y-%m-%d",   # ISO 8601 already — pass through
        "%d/%m/%Y",   # DD/MM/YYYY  (defensive fallback)
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    logger.warning("Could not parse date", extra={"value": date_str})
    return None


def clean_amount(amount_str) -> Optional[float]:
    """
    Strips currency symbols and converts to float.
    Handles: "$1234.56", "1234.56", "1,234.56", None, NaN.
    """
    if pd.isna(amount_str):
        return None
    cleaned = str(amount_str).strip().replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not parse amount", extra={"value": amount_str})
        return None


def run_cleaning_pipeline(csv_bytes: bytes) -> tuple[pd.DataFrame, int, int]:
    """
    Runs the full cleaning pipeline on raw CSV bytes.

    Returns:
        (cleaned_df, row_count_raw, row_count_clean)

    The caller (Celery task) uses row_count_raw and row_count_clean
    to update the Job record in the database.
    """
    # ── Step 1: Parse ─────────────────────────────────────────────────────────
    df = pd.read_csv(io.BytesIO(csv_bytes))
    # Normalize column names: strip whitespace, lowercase
    df.columns = [col.strip().lower() for col in df.columns]
    row_count_raw = len(df)
    logger.info("CSV parsed", extra={"row_count_raw": row_count_raw})

    # ── Step 2: Normalize dates ───────────────────────────────────────────────
    df["date"] = df["date"].apply(parse_date)

    # ── Step 3: Clean amounts ─────────────────────────────────────────────────
    df["amount"] = df["amount"].apply(clean_amount)

    # ── Step 4: Normalize casing ──────────────────────────────────────────────
    # Status: success → SUCCESS, failed → FAILED
    df["status"] = df["status"].str.strip().str.upper()
    # Currency: inr → INR, usd → USD
    df["currency"] = df["currency"].str.strip().str.upper()
    # Merchant: strip whitespace but preserve original casing
    df["merchant"] = df["merchant"].str.strip()

    # ── Step 5: Fill missing categories ──────────────────────────────────────
    # Both NaN and empty string treated as missing
    df["category"] = df["category"].replace("", pd.NA)
    df["category"] = df["category"].fillna("Uncategorised")
    df["category"] = df["category"].str.strip()

    # ── Step 6: Remove exact duplicates ───────────────────────────────────────
    # "Exact duplicate" means every column value is identical.
    # keep="first": retain the first occurrence, drop subsequent ones.
    before_dedup = len(df)
    df = df.drop_duplicates(keep="first")
    dropped = before_dedup - len(df)
    if dropped > 0:
        logger.info("Duplicate rows removed", extra={"count": dropped})

    # ── Step 7: Surrogate txn_id for blank rows ───────────────────────────────
    # Some rows have no txn_id. We generate a UUID so every transaction has
    # a unique identifier in our database. We prefix with "GEN-" to distinguish
    # system-generated IDs from original CSV IDs in debugging/audits.
    def fill_txn_id(val):
        if pd.isna(val) or str(val).strip() == "":
            return f"GEN-{uuid.uuid4().hex[:8].upper()}"
        return str(val).strip()

    df["txn_id"] = df["txn_id"].apply(fill_txn_id)

    # ── Step 8: Fill remaining NaN with None ──────────────────────────────────
    # SQLAlchemy expects Python None for NULL, not pandas NaN.
    # NaN in a string column causes "NaN" to be inserted as a string — a bug.
    df = df.where(pd.notnull(df), None)

    row_count_clean = len(df)
    logger.info(
        "Cleaning complete",
        extra={"row_count_raw": row_count_raw, "row_count_clean": row_count_clean},
    )

    return df, row_count_raw, row_count_clean