"""
src/analytics/edge_case_handler.py
====================================
Sprint 2 — Day 13
Cross-checks computed KPIs against source data and documents anomalies.

Anomaly categories
------------------
DATA_SOURCE_ISSUE    : Raw data column uses non-standard definition (e.g. banks)
VERSION_DIFFERENCE   : Screener/source uses a different period/formula version
FORMULA_DISCREPANCY  : Our formula differs from industry convention

Output
------
output/ratio_edge_cases.log — one entry per anomaly, structured as:
    [CATEGORY] company=TICKER  year=YYYY  field=FIELD  computed=X  source=Y  note=...

Run with:
    python -m src.analytics.edge_case_handler
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import config

# ─────────────────────────────────────────────────────────────────────────────
# Logging — two handlers: console (INFO) + file (all entries)
# ─────────────────────────────────────────────────────────────────────────────
LOG_PATH = config.OUTPUT_DIR / "ratio_edge_cases.log"


def _setup_logger() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("edge_case_handler")
    log.setLevel(logging.DEBUG)
    log.handlers.clear()

    # File handler — structured anomaly entries
    fh = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(message)s"))

    # Console handler — INFO level only
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))

    log.addHandler(fh)
    log.addHandler(ch)
    return log


logger = _setup_logger()

# ─────────────────────────────────────────────────────────────────────────────
# Category constants
# ─────────────────────────────────────────────────────────────────────────────
CAT_DATA_SOURCE = "DATA_SOURCE_ISSUE"
CAT_VERSION_DIFF = "VERSION_DIFFERENCE"
CAT_FORMULA_DISC = "FORMULA_DISCREPANCY"

# Financials sector — D/E warning suppressed
FINANCIALS_SECTOR = "Financials"

# Thresholds
ROCE_DIFF_THRESHOLD = 5.0  # percentage points
ROE_DIFF_THRESHOLD = 5.0  # percentage points
OPM_DIFF_THRESHOLD = 1.0  # percentage points


def _log_anomaly(
    category: str,
    company: str,
    year: Optional[int],
    field: str,
    computed: object,
    source: object,
    note: str,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"[{category}]  ts={ts}  company={company}  year={year or 'N/A'}  "
        f"field={field}  computed={computed}  source={source}  note={note}"
    )
    logger.debug(entry)


# ─────────────────────────────────────────────────────────────────────────────
# Check 1 — Suppress D/E high-leverage warning for Financials
# ─────────────────────────────────────────────────────────────────────────────


def check_financials_leverage(conn: sqlite3.Connection) -> int:
    """
    For every Financials-sector company that has high_leverage_flag=1,
    log and clear the flag (it's expected for banks/NBFCs/insurers).

    Returns count of suppressed flags.
    """
    rows = conn.execute(
        """
        SELECT fr.company_id, fr.year, fr.debt_to_equity
        FROM   financial_ratios fr
        JOIN   sectors s ON fr.company_id = s.company_id
        WHERE  s.broad_sector = ?
          AND  fr.high_leverage_flag = 1
        """,
        (FINANCIALS_SECTOR,),
    ).fetchall()

    suppressed = 0
    for company_id, year, de in rows:
        _log_anomaly(
            CAT_DATA_SOURCE,
            company_id,
            year,
            "high_leverage_flag",
            f"D/E={de:.2f} flag=1",
            "suppressed",
            "Financials sector — high leverage is structurally normal (deposits/debt = core funding)",
        )
        conn.execute(
            "UPDATE financial_ratios SET high_leverage_flag = 0 "
            "WHERE company_id = ? AND year = ?",
            (company_id, int(year)),
        )
        suppressed += 1

    if suppressed:
        conn.commit()
        logger.info("D/E leverage flags suppressed for Financials: %d", suppressed)
    return suppressed


# ─────────────────────────────────────────────────────────────────────────────
# Check 2 — OPM mismatch for Financials (data source issue)
# ─────────────────────────────────────────────────────────────────────────────


def check_opm_financials(conn: sqlite3.Connection) -> int:
    """
    For Financials companies, the stored opm_percentage in profitandloss is
    reported in absolute Cr terms (not %) by the source.  Log as DATA_SOURCE_ISSUE.
    """
    rows = conn.execute(
        """
        SELECT pl.company_id, pl.year,
               pl.operating_profit, pl.sales, pl.opm_percentage,
               fr.operating_profit_margin_pct
        FROM   profitandloss pl
        JOIN   sectors s ON pl.company_id = s.company_id
        JOIN   financial_ratios fr
               ON fr.company_id = pl.company_id AND fr.year = CAST(pl.year AS INTEGER)
        WHERE  s.broad_sector = ?
          AND  fr.operating_profit_margin_pct IS NOT NULL
          AND  ABS(fr.operating_profit_margin_pct - pl.opm_percentage) > ?
        """,
        (FINANCIALS_SECTOR, OPM_DIFF_THRESHOLD),
    ).fetchall()

    logged = 0
    companies_seen: set = set()
    for company_id, year, op, sales, opm_db, opm_computed in rows:
        companies_seen.add(company_id)
        _log_anomaly(
            CAT_DATA_SOURCE,
            company_id,
            int(year),
            "opm_percentage",
            f"{opm_computed:.2f}%",
            f"{opm_db} (absolute Cr in source)",
            "Financials sector: source stores OPM as absolute operating profit in Cr, "
            "not as a percentage.  Computed value uses standard formula (OP/Sales × 100).",
        )
        logged += 1

    logger.info(
        "OPM data-source issues logged: %d rows across %d Financials companies",
        logged,
        len(companies_seen),
    )
    return logged


# ─────────────────────────────────────────────────────────────────────────────
# Check 3 — ROCE vs companies.roce_percentage
# ─────────────────────────────────────────────────────────────────────────────


def check_roce_vs_source(conn: sqlite3.Connection) -> int:
    """
    Cross-check computed ROCE against the single snapshot value stored in
    companies.roce_percentage.  Log entries where diff > 5 pp.

    Since companies.roce_percentage is a point-in-time snapshot (likely FY2024),
    we compare only against the most recent year's computed value per company.
    """
    rows = conn.execute(
        """
        SELECT c.id AS company_id,
               c.roce_percentage AS source_roce,
               fr.year,
               fr.return_on_capital_employed_pct AS computed_roce
        FROM   companies c
        JOIN   financial_ratios fr ON fr.company_id = c.id
        WHERE  c.roce_percentage IS NOT NULL
          AND  fr.return_on_capital_employed_pct IS NOT NULL
          AND  fr.year = (
                SELECT MAX(year) FROM financial_ratios
                WHERE company_id = c.id
                  AND return_on_capital_employed_pct IS NOT NULL
              )
        """
    ).fetchall()

    logged = 0
    for company_id, source_roce, year, computed_roce in rows:
        diff = abs(computed_roce - source_roce)
        if diff > ROCE_DIFF_THRESHOLD:
            # Categorise the anomaly
            if diff > 20:
                category = CAT_DATA_SOURCE
                note = (
                    "Large gap suggests source uses a different capital base "
                    "(e.g. average capital employed vs year-end, or excludes goodwill)."
                )
            elif diff > 10:
                category = CAT_VERSION_DIFF
                note = (
                    "Moderate gap — source may use average capital employed "
                    "or a trailing-twelve-month period vs fiscal year."
                )
            else:
                category = CAT_FORMULA_DISC
                note = (
                    "Minor formula discrepancy — possible rounding or "
                    "different treatment of CWIP in capital base."
                )

            _log_anomaly(
                category,
                company_id,
                int(year),
                "return_on_capital_employed_pct",
                f"{computed_roce:.2f}%",
                f"{source_roce:.2f}%",
                note,
            )
            logged += 1

    logger.info("ROCE cross-check anomalies logged: %d", logged)
    return logged


# ─────────────────────────────────────────────────────────────────────────────
# Check 4 — ROE vs companies.roe_percentage
# ─────────────────────────────────────────────────────────────────────────────


def check_roe_vs_source(conn: sqlite3.Connection) -> int:
    """
    Cross-check computed ROE against companies.roe_percentage snapshot.
    Flags anomalies > 5 pp; notes the known TCS near-zero roe_percentage issue.
    """
    rows = conn.execute(
        """
        SELECT c.id AS company_id,
               c.roe_percentage AS source_roe,
               fr.year,
               fr.return_on_equity_pct AS computed_roe
        FROM   companies c
        JOIN   financial_ratios fr ON fr.company_id = c.id
        WHERE  c.roe_percentage IS NOT NULL
          AND  fr.return_on_equity_pct IS NOT NULL
          AND  fr.year = (
                SELECT MAX(year) FROM financial_ratios
                WHERE company_id = c.id
                  AND return_on_equity_pct IS NOT NULL
              )
        """
    ).fetchall()

    logged = 0
    for company_id, source_roe, year, computed_roe in rows:
        diff = abs(computed_roe - source_roe)
        if diff <= ROE_DIFF_THRESHOLD:
            continue

        # Known anomaly: TCS shows roe_percentage ≈ 0.52 in source
        if company_id == "TCS" and source_roe < 2.0:
            note = (
                "Known anomaly: source shows roe_percentage=0.52 (fraction, not %).  "
                "Likely a data-entry error — stored as decimal instead of percentage."
            )
            category = CAT_DATA_SOURCE
        elif diff > 20:
            category = CAT_DATA_SOURCE
            note = (
                "Large gap: source may use average equity (opening + closing / 2) "
                "vs year-end equity capital + reserves used in our formula."
            )
        elif diff > 10:
            category = CAT_VERSION_DIFF
            note = (
                "Moderate gap: source may use average equity or a different "
                "fiscal period alignment."
            )
        else:
            category = CAT_FORMULA_DISC
            note = (
                "Minor discrepancy — possible rounding or minority-interest treatment."
            )

        _log_anomaly(
            category,
            company_id,
            int(year),
            "return_on_equity_pct",
            f"{computed_roe:.2f}%",
            f"{source_roe:.2f}%",
            note,
        )
        logged += 1

    logger.info("ROE cross-check anomalies logged: %d", logged)
    return logged


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────


def run(db_path: Path = config.DB_PATH, log_path: Path = LOG_PATH) -> None:
    logger.info("=" * 70)
    logger.info("Edge Case Handler — Sprint 2 Day 13")
    logger.info("DB  : %s", db_path)
    logger.info("Log : %s", log_path)
    logger.info("=" * 70)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        fin_flags = check_financials_leverage(conn)
        opm_issues = check_opm_financials(conn)
        roce_anom = check_roce_vs_source(conn)
        roe_anom = check_roe_vs_source(conn)

    total = fin_flags + opm_issues + roce_anom + roe_anom
    logger.info("-" * 70)
    logger.info(
        "Summary — suppressed_leverage=%d  opm_issues=%d  roce_anomalies=%d  roe_anomalies=%d  total=%d",
        fin_flags,
        opm_issues,
        roce_anom,
        roe_anom,
        total,
    )
    logger.info("Log written → %s", log_path)


if __name__ == "__main__":
    run()
