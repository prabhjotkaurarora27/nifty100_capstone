"""
src/analytics/peer.py
======================
Sprint 3 — Day 18
Peer group percentile ranking for 10 metrics across 11 peer groups.
Populates the `peer_percentiles` SQLite table.

Metrics
-------
ROE, ROCE, Net Profit Margin, D/E (inverted rank), FCF, PAT CAGR 5yr,
Revenue CAGR 5yr, EPS CAGR 5yr, Interest Coverage, Asset Turnover

Run with:
    python -m src.analytics.peer
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

logger = logging.getLogger(__name__)

# ── Metrics: (column_in_financial_ratios, public_label, invert_rank) ──────────
PEER_METRICS: List[Tuple[str, str, bool]] = [
    ("return_on_equity_pct",            "ROE",                False),
    ("return_on_capital_employed_pct",  "ROCE",               False),
    ("net_profit_margin_pct",           "Net Profit Margin",  False),
    ("debt_to_equity",                  "D/E",                True),   # lower = better
    ("free_cash_flow_cr",               "FCF",                False),
    ("pat_cagr_5yr",                    "PAT CAGR 5yr",       False),
    ("revenue_cagr_5yr",                "Revenue CAGR 5yr",   False),
    ("eps_cagr_5yr",                    "EPS CAGR 5yr",       False),
    ("interest_coverage",               "Interest Coverage",  False),
    ("asset_turnover",                  "Asset Turnover",     False),
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS peer_percentiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      TEXT    NOT NULL,
    peer_group_name TEXT    NOT NULL,
    metric          TEXT    NOT NULL,
    value           REAL,
    percentile_rank REAL,
    year            INTEGER,
    UNIQUE(company_id, peer_group_name, metric)
)
"""


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_peer_groups(conn: sqlite3.Connection) -> pd.DataFrame:
    """Return peer_groups table as DataFrame."""
    return pd.read_sql_query(
        "SELECT peer_group_name, company_id, is_benchmark FROM peer_groups",
        conn,
    )


def _load_latest_ratios(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Load latest-year financial_ratios for every company that appears
    in peer_groups, plus their ICR label for Debt-Free handling.
    """
    metric_cols = ", ".join(f"fr.{col}" for col, _, _ in PEER_METRICS)
    sql = f"""
    SELECT fr.company_id, fr.year,
           fr.icr_label,
           {metric_cols}
    FROM financial_ratios fr
    WHERE fr.year = (
        SELECT MAX(year) FROM financial_ratios fr2
        WHERE fr2.company_id = fr.company_id
          AND fr2.return_on_equity_pct IS NOT NULL
    )
    """
    return pd.read_sql_query(sql, conn)


# ─────────────────────────────────────────────────────────────────────────────
# Percentile rank computation
# ─────────────────────────────────────────────────────────────────────────────

def _percent_rank(series: pd.Series, invert: bool = False) -> pd.Series:
    """
    Compute PERCENT_RANK (0.0 – 1.0) for a Series.
    Ties use average rank (method='average').
    invert=True → return (1 – rank) so lower value = higher percentile.
    """
    ranked = series.rank(method="average", na_option="keep") - 1
    max_r  = ranked.max()
    if max_r == 0:
        pr = pd.Series(0.5, index=series.index)
    else:
        pr = ranked / max_r
    pr = pr.where(series.notna(), other=float("nan"))
    if invert:
        pr = 1.0 - pr
    return pr.round(4)


def compute_peer_percentiles(db_path: Path = config.DB_PATH) -> pd.DataFrame:
    """
    Compute percentile ranks for all 10 metrics within each peer group.

    Returns
    -------
    DataFrame with columns:
        company_id, peer_group_name, metric, value, percentile_rank, year

    Notes
    -----
    * Companies with no peer group assignment are silently skipped.
    * ICR "Debt Free" label → treated as value=9999 before ranking
      (ensures they always get the highest ICR rank).
    * D/E percentile is inverted: lower D/E → higher rank.
    """
    with sqlite3.connect(db_path) as conn:
        pg_df      = _load_peer_groups(conn)
        ratios_df  = _load_latest_ratios(conn)

    # Join ratios onto peer groups
    merged = pg_df.merge(ratios_df, on="company_id", how="left")

    no_data = merged[ratios_df.columns[0]].isna().sum() if len(merged) else 0
    if no_data:
        logger.warning("%d peer-group companies have no ratio data", no_data)

    records: List[Dict] = []

    for group_name, group_df in merged.groupby("peer_group_name"):
        group_df = group_df.copy()

        for col, label, invert in PEER_METRICS:
            if col not in group_df.columns:
                continue

            # Handle ICR "Debt Free" → substitute large numeric value
            if col == "interest_coverage":
                debt_free_mask = group_df.get("icr_label") == "Debt Free"
                group_df[col]  = pd.to_numeric(group_df[col], errors="coerce")
                group_df.loc[debt_free_mask, col] = 9999.0

            series    = pd.to_numeric(group_df[col], errors="coerce")
            pr_series = _percent_rank(series, invert=invert)

            for _, row in group_df.iterrows():
                val = series.loc[row.name]
                pr  = pr_series.loc[row.name]
                records.append({
                    "company_id":      row["company_id"],
                    "peer_group_name": group_name,
                    "metric":          label,
                    "value":           None if pd.isna(val) else round(float(val), 4),
                    "percentile_rank": None if pd.isna(pr)  else round(float(pr),  4),
                    "year":            int(row["year"]) if pd.notna(row.get("year", None)) else None,
                })

    result = pd.DataFrame(records)
    logger.info("Computed %d peer percentile records (%d groups, %d metrics)",
                len(result), merged["peer_group_name"].nunique(), len(PEER_METRICS))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SQLite persistence
# ─────────────────────────────────────────────────────────────────────────────

def populate_peer_percentiles_table(db_path: Path = config.DB_PATH) -> int:
    """
    Create `peer_percentiles` table (if not exists) and upsert all records.

    Returns
    -------
    int : total rows in peer_percentiles after the run
    """
    df = compute_peer_percentiles(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)

        upserted = 0
        for _, row in df.iterrows():
            conn.execute(
                """
                INSERT INTO peer_percentiles
                    (company_id, peer_group_name, metric, value, percentile_rank, year)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id, peer_group_name, metric)
                DO UPDATE SET
                    value           = excluded.value,
                    percentile_rank = excluded.percentile_rank,
                    year            = excluded.year
                """,
                (
                    row["company_id"],
                    row["peer_group_name"],
                    row["metric"],
                    row["value"],
                    row["percentile_rank"],
                    row["year"],
                ),
            )
            upserted += 1

        conn.commit()
        total = conn.execute(
            "SELECT COUNT(*) FROM peer_percentiles"
        ).fetchone()[0]

    logger.info("✓ peer_percentiles table: %d rows upserted, %d total", upserted, total)
    return total


def get_peer_percentiles(
    db_path: Path = config.DB_PATH,
    company_id: Optional[str] = None,
    peer_group_name: Optional[str] = None,
) -> pd.DataFrame:
    """
    Query peer_percentiles table with optional filters.
    Companies with no peer group: returns empty DataFrame, no error.
    """
    sql = "SELECT * FROM peer_percentiles WHERE 1=1"
    params: List = []
    if company_id:
        sql    += " AND company_id = ?"
        params.append(company_id)
    if peer_group_name:
        sql    += " AND peer_group_name = ?"
        params.append(peer_group_name)

    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(sql, conn, params=params)
    except sqlite3.OperationalError:
        logger.warning("peer_percentiles table does not exist yet")
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    total = populate_peer_percentiles_table()
    print(f"\n✓ peer_percentiles table populated — {total} rows")

    # Quick spot-check: IT Services ROE ranking
    print("\n── IT Services — ROE Percentile Ranks ───────────────────")
    with sqlite3.connect(config.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT company_id, value, percentile_rank
            FROM peer_percentiles
            WHERE peer_group_name = 'IT Services' AND metric = 'ROE'
            ORDER BY percentile_rank DESC
            """
        ).fetchall()
    for r in rows:
        print(f"  {r[0]:<15} ROE={r[1]:.2f}%  Percentile={r[2]:.3f}")
