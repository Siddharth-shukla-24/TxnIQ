"""
Anomaly detection pipeline — Step (b) of the processing spec.

Two detection rules:
  Rule 1 — Statistical outlier:
      Amount > 3x the account's median transaction amount.
      Computed per account_id using the cleaned DataFrame.

  Rule 2 — Currency mismatch:
      Currency is USD but merchant is a known domestic-only brand
      (Swiggy, Ola, IRCTC, Zomato, Jio Recharge, BookMyShow, HDFC ATM).
      These brands don't accept USD — a USD transaction is fraudulent or erroneous.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Known domestic-only merchants — should never appear with USD currency.
# Case-insensitive matching applied during detection.
DOMESTIC_ONLY_MERCHANTS = {
    "swiggy", "ola", "irctc", "zomato",
    "jio recharge", "bookmyshow", "hdfc atm",
}


def run_anomaly_detection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds `is_anomaly` (bool) and `anomaly_reason` (str|None) columns to df.

    Modifies the DataFrame in place and also returns it for chaining.
    A transaction can be flagged for BOTH reasons simultaneously — the
    anomaly_reason field concatenates both with ' | ' in that case.

    Args:
        df: Cleaned DataFrame from run_cleaning_pipeline()

    Returns:
        Same DataFrame with anomaly columns populated.
    """
    # Initialize anomaly columns
    df["is_anomaly"] = False
    df["anomaly_reason"] = None

    # ── Rule 1: Statistical outlier (per account median) ──────────────────────
    df = _flag_statistical_outliers(df)

    # ── Rule 2: Domestic merchant with USD currency ───────────────────────────
    df = _flag_currency_mismatches(df)

    anomaly_count = df["is_anomaly"].sum()
    logger.info(
        "Anomaly detection complete",
        extra={"anomalies_found": int(anomaly_count)},
    )

    return df


def _flag_statistical_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flags transactions where amount > 3x the account's median amount.

    Only considers rows with valid (non-null) amounts for median calculation.
    Rows with null amounts are skipped — can't determine if they're outliers.
    """
    # Filter to rows with valid amounts for median calculation
    valid_amounts = df[df["amount"].notna() & (df["amount"] > 0)]

    if valid_amounts.empty:
        return df

    # groupby account_id, compute median amount per group
    # Result: {"ACC001": 1500.0, "ACC002": 800.0, ...}
    account_medians: pd.Series = valid_amounts.groupby("account_id")["amount"].median()

    for idx, row in df.iterrows():
        if pd.isna(row.get("amount")) or pd.isna(row.get("account_id")):
            continue

        account = row["account_id"]
        if account not in account_medians.index:
            continue

        median = account_medians[account]

        # Guard against division by zero (all transactions are 0.00)
        if median == 0:
            continue

        if row["amount"] > 3 * median:
            reason = (
                f"Amount {row['amount']:.2f} exceeds 3x account median "
                f"{median:.2f} for account {account}"
            )
            df.at[idx, "is_anomaly"] = True
            df.at[idx, "anomaly_reason"] = _append_reason(
                df.at[idx, "anomaly_reason"], reason
            )

    return df


def _flag_currency_mismatches(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flags transactions where currency=USD but merchant is domestic-only.
    """
    for idx, row in df.iterrows():
        currency = str(row.get("currency") or "").upper()
        merchant = str(row.get("merchant") or "").lower().strip()

        if currency == "USD" and merchant in DOMESTIC_ONLY_MERCHANTS:
            reason = (
                f"USD currency used with domestic-only merchant '{row['merchant']}'"
            )
            df.at[idx, "is_anomaly"] = True
            df.at[idx, "anomaly_reason"] = _append_reason(
                df.at[idx, "anomaly_reason"], reason
            )

    return df


def _append_reason(existing: Optional[str], new_reason: str) -> str:
    """Concatenates anomaly reasons if a row is flagged by multiple rules."""
    if existing:
        return f"{existing} | {new_reason}"
    return new_reason