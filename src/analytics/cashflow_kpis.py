"""
src/analytics/cashflow_kpis.py
==============================
Sprint 2 — Day 11
Cash-flow derived KPIs and capital-allocation classifier.

Public API
----------
free_cash_flow(operating_activity, investing_activity)
cfo_quality_score(cfo_list, pat_list)
capex_intensity(investing_activity, sales)
fcf_conversion_rate(fcf, operating_profit)
classify_capital_allocation(cfo_sign, cfi_sign, cff_sign)
generate_capital_allocation_csv(db_path, output_path)
"""

from __future__ import annotations

import csv
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Capital-allocation pattern labels
# ─────────────────────────────────────────────────────────────────────────────
PATTERN_REINVESTOR = "Reinvestor"
PATTERN_SHAREHOLDER_RETURNS = "Shareholder Returns"
PATTERN_LIQUIDATING_ASSETS = "Liquidating Assets"
PATTERN_DISTRESS_SIGNAL = "Distress Signal"
PATTERN_GROWTH_BY_DEBT = "Growth Funded by Debt"
PATTERN_CASH_ACCUMULATOR = "Cash Accumulator"
PATTERN_PRE_REVENUE = "Pre-Revenue"
PATTERN_MIXED = "Mixed"

# CFO, CFI, CFF sign → pattern
# Sign convention: +1=positive, -1=negative, 0=zero treated as non-negative
_ALLOCATION_MAP: dict[tuple, str] = {
    (+1, -1, -1): PATTERN_REINVESTOR,          # healthy: earns, invests, repays
    (+1, -1, +1): PATTERN_GROWTH_BY_DEBT,      # earns + investing, financed by debt
    (+1, +1, -1): PATTERN_SHAREHOLDER_RETURNS, # earns + sells assets, returns to shareholders
    (+1, +1, +1): PATTERN_CASH_ACCUMULATOR,    # all positive — building cash war chest
    (-1, +1, +1): PATTERN_LIQUIDATING_ASSETS,  # burning cash, selling assets, raising debt
    (-1, -1, +1): PATTERN_PRE_REVENUE,         # start-up / heavy capex, funded by equity/debt
    (-1, +1, -1): PATTERN_DISTRESS_SIGNAL,     # burning cash, selling assets, also repaying debt
    (-1, -1, -1): PATTERN_MIXED,               # all negative — uncommon / distress
}


def _sign(value: Optional[float]) -> int:
    """Return +1 for positive, -1 for non-positive (treats 0 as negative)."""
    if value is None or value <= 0:
        return -1
    return +1


# ─────────────────────────────────────────────────────────────────────────────
# Pure KPI functions
# ─────────────────────────────────────────────────────────────────────────────

def free_cash_flow(
    operating_activity: Optional[float],
    investing_activity: Optional[float],
) -> Optional[float]:
    """
    Free Cash Flow (Cr).

    FCF = Cash from Operations + Cash from Investing

    Note: investing_activity is typically negative (outflow), so
    FCF = CFO − CapEx (broadly).  We add directly because the DB
    stores investing_activity as a signed value.

    Returns None if both inputs are None.
    """
    if operating_activity is None and investing_activity is None:
        return None
    cfo = operating_activity or 0.0
    cfi = investing_activity or 0.0
    return round(cfo + cfi, 4)


def cfo_quality_score(
    cfo_list: List[Optional[float]],
    pat_list: List[Optional[float]],
) -> str:
    """
    CFO Quality Score — measures earnings quality via cash conversion.

    Computes average CFO/PAT ratio over the supplied years (up to 5).
    Only years where both CFO and PAT are non-None and PAT ≠ 0 are used.

    Thresholds
    ----------
    avg ≥ 0.75  → "High Quality"
    avg ≥ 0.40  → "Moderate"
    else        → "Accrual Risk"

    Returns "Insufficient Data" when fewer than 2 valid pairs exist.
    """
    ratios = []
    for cfo, pat in zip(cfo_list, pat_list):
        if cfo is not None and pat is not None and pat != 0:
            ratios.append(cfo / pat)

    if len(ratios) < 2:
        return "Insufficient Data"

    avg = sum(ratios) / len(ratios)
    if avg >= 0.75:
        return "High Quality"
    if avg >= 0.40:
        return "Moderate"
    return "Accrual Risk"


def capex_intensity(
    investing_activity: Optional[float],
    sales: Optional[float],
) -> Optional[str]:
    """
    CapEx Intensity Label.

    Proxy: |investing_activity| / sales
    (investing_activity is typically negative in DB — we take absolute value)

    Thresholds
    ----------
    < 0.05   → "Asset Light"
    < 0.15   → "Moderate"
    ≥ 0.15   → "Capital Intensive"

    Returns None if sales is 0 or None.
    """
    if sales is None or sales == 0 or investing_activity is None:
        return None
    intensity = abs(investing_activity) / abs(sales)
    if intensity < 0.05:
        return "Asset Light"
    if intensity < 0.15:
        return "Moderate"
    return "Capital Intensive"


def fcf_conversion_rate(
    fcf: Optional[float],
    operating_profit: Optional[float],
) -> Optional[float]:
    """
    FCF Conversion Rate.

    FCF Conversion = Free Cash Flow / Operating Profit

    Returns None if operating_profit is 0 or None.
    """
    if fcf is None or operating_profit is None:
        return None
    if operating_profit == 0:
        return None
    return round(fcf / operating_profit, 4)


def classify_capital_allocation(
    cfo: Optional[float],
    cfi: Optional[float],
    cff: Optional[float],
) -> str:
    """
    Classify capital allocation pattern based on signs of CFO, CFI, CFF.

    Uses 8-bucket sign-pattern lookup table.  Returns PATTERN_MIXED as
    default if the combination isn't in the map (shouldn't happen).
    """
    key = (_sign(cfo), _sign(cfi), _sign(cff))
    return _ALLOCATION_MAP.get(key, PATTERN_MIXED)


# ─────────────────────────────────────────────────────────────────────────────
# CSV generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_capital_allocation_csv(
    db_path: Path,
    output_path: Path,
) -> int:
    """
    Read all cashflow rows and write capital-allocation pattern to CSV.

    Output columns
    --------------
    company_id, year, cfo_sign, cfi_sign, cff_sign, pattern_label

    Returns
    -------
    int : number of rows written
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT company_id, year,
                   operating_activity, investing_activity, financing_activity
            FROM   cashflow
            ORDER  BY company_id, year
            """
        ).fetchall()

    written = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company_id", "year",
                "cfo_sign", "cfi_sign", "cff_sign",
                "pattern_label",
            ],
        )
        writer.writeheader()

        for row in rows:
            cfo = row["operating_activity"]
            cfi = row["investing_activity"]
            cff = row["financing_activity"]
            pattern = classify_capital_allocation(cfo, cfi, cff)

            writer.writerow({
                "company_id":    row["company_id"],
                "year":          int(row["year"]),
                "cfo_sign":      _sign(cfo),
                "cfi_sign":      _sign(cfi),
                "cff_sign":      _sign(cff),
                "pattern_label": pattern,
            })
            written += 1

    logger.info("Capital allocation CSV written → %s  (%d rows)", output_path, written)
    return written
