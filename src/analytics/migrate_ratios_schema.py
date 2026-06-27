"""
src/analytics/migrate_ratios_schema.py
=======================================
Sprint 2 — Day 12 (run once before ratio_engine.py)
Adds all KPI columns to the existing financial_ratios table.

Run with:
    python -m src.analytics.migrate_ratios_schema

Safe to re-run — uses try/except to skip columns that already exist.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# New columns to add — (column_name, sqlite_type)
NEW_COLUMNS: list[tuple[str, str]] = [
    ("net_profit_margin_pct",           "REAL"),
    ("operating_profit_margin_pct",     "REAL"),
    ("return_on_equity_pct",            "REAL"),
    ("return_on_capital_employed_pct",  "REAL"),
    ("return_on_assets_pct",            "REAL"),
    ("debt_to_equity",                  "REAL"),
    ("high_leverage_flag",              "INTEGER"),
    ("interest_coverage",               "REAL"),
    ("icr_label",                       "TEXT"),
    ("icr_warning_flag",                "INTEGER"),
    ("net_debt_cr",                     "REAL"),
    ("asset_turnover",                  "REAL"),
    ("free_cash_flow_cr",               "REAL"),
    ("capex_intensity_label",           "TEXT"),
    ("fcf_conversion_rate",             "REAL"),
    ("cfo_quality_score",               "TEXT"),
    ("capital_allocation_pattern",      "TEXT"),
    ("revenue_cagr_3yr",                "REAL"),
    ("revenue_cagr_5yr",                "REAL"),
    ("revenue_cagr_10yr",               "REAL"),
    ("revenue_cagr_5yr_flag",           "TEXT"),
    ("pat_cagr_3yr",                    "REAL"),
    ("pat_cagr_5yr",                    "REAL"),
    ("pat_cagr_10yr",                   "REAL"),
    ("pat_cagr_5yr_flag",               "TEXT"),
    ("eps_cagr_3yr",                    "REAL"),
    ("eps_cagr_5yr",                    "REAL"),
    ("eps_cagr_10yr",                   "REAL"),
    ("eps_cagr_5yr_flag",               "TEXT"),
    ("composite_quality_score",         "REAL"),
]


def migrate(db_path: Path = config.DB_PATH) -> None:
    added = 0
    skipped = 0

    with sqlite3.connect(db_path) as conn:
        existing_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(financial_ratios)")
        }

        for col_name, col_type in NEW_COLUMNS:
            if col_name in existing_cols:
                logger.debug("Column already exists — skipping: %s", col_name)
                skipped += 1
                continue
            try:
                conn.execute(
                    f"ALTER TABLE financial_ratios ADD COLUMN {col_name} {col_type}"
                )
                logger.info("Added column: %s %s", col_name, col_type)
                added += 1
            except sqlite3.OperationalError as exc:
                logger.warning("Could not add %s: %s", col_name, exc)
                skipped += 1

        conn.commit()

    logger.info("Migration complete — added=%d  skipped=%d", added, skipped)


if __name__ == "__main__":
    migrate()
