"""
src/analytics/ratio_engine.py
==============================
Sprint 2 — Day 12
Full Ratio Engine — computes all 30 KPI columns for all 92 companies
across all available years and upserts into financial_ratios table.

Strategy
--------
* Load P&L, BS, CF for every company grouped by year
* For each (company_id, year) pair:
    - Compute all margin/return/leverage/cashflow KPIs
    - Compute CAGR windows (anchored at each year against n years back)
    - Compute CFO quality score from rolling 5-year window
    - Classify capital allocation pattern
* UPDATE rows that already exist in financial_ratios
* INSERT rows that are missing
* Verify COUNT(*) >= 1100 at the end

Run with:
    python -m src.analytics.ratio_engine
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import config
from src.analytics.cagr import compute_cagr
from src.analytics.cashflow_kpis import (
    capex_intensity,
    cfo_quality_score,
    classify_capital_allocation,
    fcf_conversion_rate,
    free_cash_flow,
)
from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_company_sector_map(conn: sqlite3.Connection) -> Dict[str, bool]:
    """Return {company_id: is_financial}."""
    rows = conn.execute(
        "SELECT company_id, broad_sector FROM sectors"
    ).fetchall()
    return {r[0]: (r[1] == "Financials") for r in rows}


def _load_pl(conn: sqlite3.Connection) -> Dict[str, Dict[int, Dict]]:
    """
    Returns {company_id: {year: {field: value, ...}}}
    """
    rows = conn.execute(
        """
        SELECT company_id, year, sales, operating_profit, opm_percentage,
               other_income, interest, profit_before_tax, net_profit, eps,
               dividend_payout
        FROM   profitandloss
        ORDER  BY company_id, year
        """
    ).fetchall()
    result: Dict[str, Dict[int, Dict]] = defaultdict(dict)
    for r in rows:
        cid, yr = r[0], int(r[1])
        result[cid][yr] = {
            "sales":             r[2],
            "operating_profit":  r[3],
            "opm_percentage":    r[4],
            "other_income":      r[5],
            "interest":          r[6],
            "profit_before_tax": r[7],
            "net_profit":        r[8],
            "eps":               r[9],
            "dividend_payout":   r[10],
        }
    return dict(result)


def _load_bs(conn: sqlite3.Connection) -> Dict[str, Dict[int, Dict]]:
    rows = conn.execute(
        """
        SELECT company_id, year, equity_capital, reserves, borrowings,
               investments, total_assets
        FROM   balancesheet
        ORDER  BY company_id, year
        """
    ).fetchall()
    result: Dict[str, Dict[int, Dict]] = defaultdict(dict)
    for r in rows:
        cid, yr = r[0], int(r[1])
        result[cid][yr] = {
            "equity_capital": r[2],
            "reserves":       r[3],
            "borrowings":     r[4],
            "investments":    r[5],
            "total_assets":   r[6],
        }
    return dict(result)


def _load_cf(conn: sqlite3.Connection) -> Dict[str, Dict[int, Dict]]:
    rows = conn.execute(
        """
        SELECT company_id, year,
               operating_activity, investing_activity, financing_activity
        FROM   cashflow
        ORDER  BY company_id, year
        """
    ).fetchall()
    result: Dict[str, Dict[int, Dict]] = defaultdict(dict)
    for r in rows:
        cid, yr = r[0], int(r[1])
        result[cid][yr] = {
            "operating_activity":  r[2],
            "investing_activity":  r[3],
            "financing_activity":  r[4],
        }
    return dict(result)


def _existing_ratio_keys(conn: sqlite3.Connection) -> set[Tuple[str, int]]:
    rows = conn.execute("SELECT company_id, year FROM financial_ratios").fetchall()
    return {(r[0], int(r[1])) for r in rows}


# ─────────────────────────────────────────────────────────────────────────────
# KPI computation for a single (company, year)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_kpis(
    company_id: str,
    year: int,
    pl: Dict,
    bs: Dict,
    cf: Dict,
    is_financial: bool,
    pl_series: Dict[int, Dict],
    cf_series: Dict[int, Dict],
) -> Dict[str, Any]:
    """
    Compute all KPI values for one (company, year) row.
    pl, bs, cf are the single-year dicts; *_series are the full time series.
    """
    kpis: Dict[str, Any] = {}

    # ── Margin & Return ratios ───────────────────────────────────────────────
    sales  = pl.get("sales")
    op     = pl.get("operating_profit")
    opm_db = pl.get("opm_percentage")
    oi     = pl.get("other_income")
    intr   = pl.get("interest")
    pbt    = pl.get("profit_before_tax")
    np_    = pl.get("net_profit")
    eps    = pl.get("eps")
    div    = pl.get("dividend_payout")

    eq_cap = bs.get("equity_capital")
    res    = bs.get("reserves")
    borr   = bs.get("borrowings")
    inv    = bs.get("investments")
    ta     = bs.get("total_assets")

    cfo    = cf.get("operating_activity")
    cfi    = cf.get("investing_activity")
    cff    = cf.get("financing_activity")

    # EBIT = PBT + Interest (standard form)
    ebit: Optional[float] = None
    if pbt is not None and intr is not None:
        ebit = pbt + intr
    elif pbt is not None:
        ebit = pbt

    kpis["net_profit_margin_pct"] = net_profit_margin(np_, sales)
    kpis["operating_profit_margin_pct"] = operating_profit_margin(
        op, sales, opm_db, company_id, year
    )
    kpis["return_on_equity_pct"] = return_on_equity(np_, eq_cap, res)
    kpis["return_on_capital_employed_pct"] = return_on_capital_employed(
        ebit, eq_cap, res, borr, is_financial
    )
    kpis["return_on_assets_pct"] = return_on_assets(np_, ta)

    # ── Leverage ratios ──────────────────────────────────────────────────────
    de = debt_to_equity(borr, eq_cap, res)
    kpis["debt_to_equity"] = de
    kpis["high_leverage_flag"] = 1 if high_leverage_flag(de, is_financial) else 0

    icr_val, icr_label, icr_warn = interest_coverage(op, oi, intr)
    kpis["interest_coverage"] = icr_val
    kpis["icr_label"]         = icr_label
    kpis["icr_warning_flag"]  = 1 if icr_warn else 0

    kpis["net_debt_cr"]   = net_debt(borr, inv)
    kpis["asset_turnover"] = asset_turnover(sales, ta)

    # ── Cash-flow KPIs ───────────────────────────────────────────────────────
    fcf_val = free_cash_flow(cfo, cfi)
    kpis["free_cash_flow_cr"]     = fcf_val
    kpis["capex_intensity_label"] = capex_intensity(cfi, sales)
    kpis["fcf_conversion_rate"]   = fcf_conversion_rate(fcf_val, op)
    kpis["capital_allocation_pattern"] = classify_capital_allocation(cfo, cfi, cff)

    # CFO quality — rolling 5-year window ending at current year
    cfo_window = [
        cf_series.get(yr, {}).get("operating_activity")
        for yr in range(year - 4, year + 1)
    ]
    pat_window = [
        pl_series.get(yr, {}).get("net_profit")
        for yr in range(year - 4, year + 1)
    ]
    kpis["cfo_quality_score"] = cfo_quality_score(cfo_window, pat_window)

    # ── CAGR (single-year anchor = current year) ──────────────────────────────
    rev_series = {yr: d.get("sales")      for yr, d in pl_series.items()}
    pat_series = {yr: d.get("net_profit") for yr, d in pl_series.items()}
    eps_series = {yr: d.get("eps")        for yr, d in pl_series.items()}

    for window, col_suffix in [(3, "3yr"), (5, "5yr"), (10, "10yr")]:
        start_yr = year - window
        for metric, series, prefix in [
            ("revenue", rev_series, "revenue"),
            ("pat",     pat_series, "pat"),
            ("eps",     eps_series, "eps"),
        ]:
            start_val = series.get(start_yr)
            end_val   = series.get(year)
            val, flag = compute_cagr(start_val, end_val, window)
            kpis[f"{prefix}_cagr_{col_suffix}"] = val
            if col_suffix == "5yr":
                kpis[f"{prefix}_cagr_5yr_flag"] = flag

    # ── Composite quality score ───────────────────────────────────────────────
    # Simple average of z-scored signals; use a weighted heuristic instead:
    # ROE × 0.3 + ROA × 0.2 + ICR (capped at 10) × 0.05 + FCF conv × 0.25 + OPM × 0.2
    try:
        roe_s   = (kpis.get("return_on_equity_pct") or 0.0) * 0.30
        roa_s   = (kpis.get("return_on_assets_pct") or 0.0) * 0.20
        icr_s   = min((kpis.get("interest_coverage") or 0.0), 10.0) * 0.50
        fcf_s   = (kpis.get("fcf_conversion_rate") or 0.0) * 25.0
        opm_s   = (kpis.get("operating_profit_margin_pct") or 0.0) * 0.20
        composite = round(roe_s + roa_s + icr_s + fcf_s + opm_s, 4)
        kpis["composite_quality_score"] = composite
    except Exception:
        kpis["composite_quality_score"] = None

    return kpis


# ─────────────────────────────────────────────────────────────────────────────
# UPSERT helpers
# ─────────────────────────────────────────────────────────────────────────────

_KPI_COLUMNS = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
    "debt_to_equity",
    "high_leverage_flag",
    "interest_coverage",
    "icr_label",
    "icr_warning_flag",
    "net_debt_cr",
    "asset_turnover",
    "free_cash_flow_cr",
    "capex_intensity_label",
    "fcf_conversion_rate",
    "cfo_quality_score",
    "capital_allocation_pattern",
    "revenue_cagr_3yr",
    "revenue_cagr_5yr",
    "revenue_cagr_10yr",
    "revenue_cagr_5yr_flag",
    "pat_cagr_3yr",
    "pat_cagr_5yr",
    "pat_cagr_10yr",
    "pat_cagr_5yr_flag",
    "eps_cagr_3yr",
    "eps_cagr_5yr",
    "eps_cagr_10yr",
    "eps_cagr_5yr_flag",
    "composite_quality_score",
]


def _update_existing(conn: sqlite3.Connection, company_id: str, year: int,
                     kpis: Dict[str, Any]) -> None:
    set_clause = ", ".join(f"{col} = ?" for col in _KPI_COLUMNS)
    values = [kpis.get(col) for col in _KPI_COLUMNS]
    values.extend([company_id, year])
    conn.execute(
        f"UPDATE financial_ratios SET {set_clause} "
        f"WHERE company_id = ? AND year = ?",
        values,
    )


def _insert_new(conn: sqlite3.Connection, company_id: str, year: int,
                kpis: Dict[str, Any]) -> None:
    cols = ["company_id", "year"] + _KPI_COLUMNS
    placeholders = ", ".join("?" for _ in cols)
    values = [company_id, year] + [kpis.get(col) for col in _KPI_COLUMNS]
    conn.execute(
        f"INSERT INTO financial_ratios ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

def run(db_path: Path = config.DB_PATH) -> int:
    """
    Run the full ratio engine.

    Returns
    -------
    int : total rows in financial_ratios after the run
    """
    logger.info("Starting Ratio Engine — DB: %s", db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        sector_map   = _load_company_sector_map(conn)
        pl_all       = _load_pl(conn)
        bs_all       = _load_bs(conn)
        cf_all       = _load_cf(conn)
        existing_keys = _existing_ratio_keys(conn)

        companies = sorted(set(pl_all) | set(bs_all))
        logger.info("Companies found: %d", len(companies))

        updated = inserted = skipped = 0

        for company_id in companies:
            is_fin     = sector_map.get(company_id, False)
            pl_series  = pl_all.get(company_id, {})
            bs_series  = bs_all.get(company_id, {})
            cf_series  = cf_all.get(company_id, {})
            all_years  = sorted(set(pl_series) | set(bs_series))

            for year in all_years:
                pl = pl_series.get(year, {})
                bs = bs_series.get(year, {})
                cf = cf_series.get(year, {})

                try:
                    kpis = _compute_kpis(
                        company_id, year, pl, bs, cf,
                        is_fin, pl_series, cf_series,
                    )
                except Exception as exc:
                    logger.warning("KPI compute error %s/%d: %s", company_id, year, exc)
                    skipped += 1
                    continue

                if (company_id, year) in existing_keys:
                    _update_existing(conn, company_id, year, kpis)
                    updated += 1
                else:
                    _insert_new(conn, company_id, year, kpis)
                    inserted += 1

        conn.commit()

        total = conn.execute(
            "SELECT COUNT(*) FROM financial_ratios"
        ).fetchone()[0]

    logger.info(
        "Ratio Engine complete — updated=%d  inserted=%d  skipped=%d  total=%d",
        updated, inserted, skipped, total,
    )

    if total < 1100:
        logger.error(
            "EXIT CRITERION FAILED: financial_ratios has %d rows (need >= 1100)", total
        )
    else:
        logger.info("✓ EXIT CRITERION MET: %d rows >= 1100", total)

    return total


if __name__ == "__main__":
    run()
