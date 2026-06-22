"""
src/etl/loader.py
-----------------
Reads 12 source files (7 core + 5 supplementary) from data/raw/,
normalises them, loads into SQLite, and writes output/load_audit.csv.

Usage
-----
    python src/etl/loader.py
"""

from __future__ import annotations

import csv
import sqlite3
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Resolve project root via this file's location
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Import project config (uses python-dotenv)
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, str(BASE_DIR))

try:
    import config as _cfg
    DB_PATH: Path     = Path(_cfg.DB_PATH)
    DATA_RAW_DIR: Path = Path(_cfg.DATA_RAW_DIR)
    OUTPUT_DIR: Path  = Path(_cfg.OUTPUT_DIR)
except Exception:  # fallback if config.py uses dotenv paths relative to cwd
    from dotenv import load_dotenv
    import os
    load_dotenv(BASE_DIR / ".env")
    DB_PATH      = BASE_DIR / os.getenv("DB_PATH",      "db/nifty100.db")
    DATA_RAW_DIR = BASE_DIR / os.getenv("DATA_RAW_DIR", "data/raw")
    OUTPUT_DIR   = BASE_DIR / os.getenv("OUTPUT_DIR",   "output")

# Make DB_PATH, DATA_RAW_DIR, OUTPUT_DIR absolute
if not DB_PATH.is_absolute():
    DB_PATH = BASE_DIR / DB_PATH
if not DATA_RAW_DIR.is_absolute():
    DATA_RAW_DIR = BASE_DIR / DATA_RAW_DIR
if not OUTPUT_DIR.is_absolute():
    OUTPUT_DIR = BASE_DIR / OUTPUT_DIR

AUDIT_FILE: Path = OUTPUT_DIR / "load_audit.csv"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logger.add(OUTPUT_DIR / "pipeline.log", rotation="10 MB", level="DEBUG", encoding="utf-8")

# ---------------------------------------------------------------------------
# Source-file catalogue
# ---------------------------------------------------------------------------
# Each entry: (filename, table_name, load_type, year_cols, ticker_cols)
#   load_type: "core" → if_exists="replace"
#              "supplementary" → if_exists="append"

SOURCE_FILES: list[dict] = [
    # ── CORE (7) ──────────────────────────────────────────────────────────
    {
        "filename": "companies.xlsx",
        "table":    "companies",
        "type":     "core",
        "year_cols":   [],
        "ticker_cols": ["ticker", "symbol", "nse_symbol", "bse_symbol"],
    },
    {
        "filename": "profit_and_loss.xlsx",
        "table":    "profitandloss",
        "type":     "core",
        "year_cols":   ["year", "fiscal_year", "fy"],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "balance_sheet.xlsx",
        "table":    "balancesheet",
        "type":     "core",
        "year_cols":   ["year", "fiscal_year", "fy"],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "cash_flow.xlsx",
        "table":    "cashflow",
        "type":     "core",
        "year_cols":   ["year", "fiscal_year", "fy"],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "analysis.xlsx",
        "table":    "analysis",
        "type":     "core",
        "year_cols":   ["year", "fiscal_year"],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "documents.xlsx",
        "table":    "documents",
        "type":     "core",
        "year_cols":   ["year", "fiscal_year"],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "pros_and_cons.xlsx",
        "table":    "prosandcons",
        "type":     "core",
        "year_cols":   [],
        "ticker_cols": ["ticker", "symbol"],
    },
    # ── SUPPLEMENTARY (5) ─────────────────────────────────────────────────
    {
        "filename": "sectors.xlsx",
        "table":    "sectors",
        "type":     "supplementary",
        "year_cols":   [],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "stock_prices.csv",
        "table":    "stock_prices",
        "type":     "supplementary",
        "year_cols":   [],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "financial_ratios.xlsx",
        "table":    "financial_ratios",
        "type":     "supplementary",
        "year_cols":   ["year", "fiscal_year", "fy"],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "peer_groups.xlsx",
        "table":    "peer_groups",
        "type":     "supplementary",
        "year_cols":   [],
        "ticker_cols": ["ticker", "symbol"],
    },
    {
        "filename": "prosandcons_extra.csv",
        "table":    "prosandcons",
        "type":     "supplementary",
        "year_cols":   [],
        "ticker_cols": ["ticker", "symbol"],
    },
]

# ---------------------------------------------------------------------------
# Normaliser imports
# ---------------------------------------------------------------------------
from src.etl.normaliser import normalize_year, normalize_ticker  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip, replace spaces with underscore in column names."""
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_")
        for c in df.columns
    ]
    return df


def apply_normalisations(
    df: pd.DataFrame,
    year_cols: list[str],
    ticker_cols: list[str],
) -> tuple[pd.DataFrame, int]:
    """
    Apply year/ticker normalisation to the relevant columns.

    Returns
    -------
    (normalised_df, rows_rejected)
        rows_rejected – rows dropped because ticker/year resulted in all-None
    """
    df = df.copy()

    for col in year_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_year)
            logger.debug(f"  normalised year column '{col}'")

    for col in ticker_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_ticker)
            logger.debug(f"  normalised ticker column '{col}'")

    # Track rows where ALL ticker columns are None (un-identifiable rows)
    active_ticker_cols = [c for c in ticker_cols if c in df.columns]
    if active_ticker_cols:
        bad_mask = df[active_ticker_cols].isnull().all(axis=1)
        rows_rejected = int(bad_mask.sum())
        df = df[~bad_mask].copy()
    else:
        rows_rejected = 0

    return df, rows_rejected


def _read_file(path: Path) -> pd.DataFrame:
    """Read a .xlsx or .csv file into a DataFrame."""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path, engine="openpyxl")
    elif suffix == ".csv":
        return pd.read_csv(path, encoding="utf-8", low_memory=False)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")


def load_table(
    df: pd.DataFrame,
    table: str,
    load_type: str,
    conn: sqlite3.Connection,
) -> int:
    """
    Write DataFrame to SQLite.  Core → replace, Supplementary → append.

    Returns rows_loaded.
    """
    if_exists = "replace" if load_type == "core" else "append"
    df.to_sql(table, conn, if_exists=if_exists, index=False)
    cur = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
    count = cur.fetchone()[0]
    logger.info(f"  [{table}] total rows in table after load: {count}")
    return len(df)


def _run_foreign_key_check(conn: sqlite3.Connection) -> None:
    """Run PRAGMA foreign_key_check and log any violations."""
    conn.execute("PRAGMA foreign_keys = ON;")
    rows = conn.execute("PRAGMA foreign_key_check;").fetchall()
    if rows:
        logger.warning(f"Foreign key violations found: {rows}")
    else:
        logger.info("PRAGMA foreign_key_check: no violations ✅")


def _write_audit(records: list[dict]) -> None:
    """Write the load audit CSV."""
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "filename", "table", "type", "status",
        "rows_loaded", "rows_rejected", "timestamp", "error",
    ]
    with AUDIT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Audit file written → {AUDIT_FILE}")


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def run_pipeline() -> None:
    """Execute the full ETL load pipeline."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting ETL pipeline")
    logger.info(f"  DB       : {DB_PATH}")
    logger.info(f"  DATA_RAW : {DATA_RAW_DIR}")
    logger.info(f"  OUTPUT   : {OUTPUT_DIR}")

    audit_records: list[dict] = []
    conn = sqlite3.connect(DB_PATH)

    try:
        for entry in tqdm(SOURCE_FILES, desc="Loading tables", unit="file"):
            filename   = entry["filename"]
            table      = entry["table"]
            load_type  = entry["type"]
            year_cols  = entry["year_cols"]
            ticker_cols = entry["ticker_cols"]
            file_path  = DATA_RAW_DIR / filename
            ts         = datetime.now().isoformat(timespec="seconds")

            record = {
                "filename": filename,
                "table":    table,
                "type":     load_type,
                "status":   "skipped",
                "rows_loaded":   0,
                "rows_rejected": 0,
                "timestamp": ts,
                "error":    "",
            }

            if not file_path.exists():
                logger.warning(f"File not found, skipping: {file_path}")
                record["status"] = "skipped_missing"
                audit_records.append(record)
                continue

            try:
                logger.info(f"Processing: {filename} → [{table}]")
                df = _read_file(file_path)
                df = _normalise_columns(df)
                df, rows_rejected = apply_normalisations(df, year_cols, ticker_cols)
                rows_loaded = load_table(df, table, load_type, conn)

                record["status"]        = "success"
                record["rows_loaded"]   = rows_loaded
                record["rows_rejected"] = rows_rejected
                record["timestamp"]     = datetime.now().isoformat(timespec="seconds")

                logger.success(f"  ✅ {filename}: loaded {rows_loaded} rows, rejected {rows_rejected}")

            except Exception as exc:  # noqa: BLE001
                tb = traceback.format_exc()
                logger.error(f"  ❌ {filename}: {exc}\n{tb}")
                record["status"] = "error"
                record["error"]  = str(exc)

            audit_records.append(record)

        # Foreign key check
        _run_foreign_key_check(conn)

    finally:
        conn.close()

    _write_audit(audit_records)

    success_count = sum(1 for r in audit_records if r["status"] == "success")
    total         = len(audit_records)
    logger.info(f"Pipeline complete: {success_count}/{total} files loaded successfully.")


if __name__ == "__main__":
    run_pipeline()
