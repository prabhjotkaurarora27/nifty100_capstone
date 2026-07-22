"""
src/analytics/demo_ratios.py
==============================
Sprint 2 — Day 14
Demo script: show all computed KPIs for 5 representative companies.

Companies chosen to cover variety:
  TCS        — IT, large-cap, high ROE
  HDFCBANK   — Financials (bank)
  RELIANCE   — Energy/Conglomerate
  SUNPHARMA  — Healthcare
  TATAMOTORS — Consumer Discretionary (auto)

Run with:
    python -m src.analytics.demo_ratios
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import config

DEMO_COMPANIES = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATAMOTORS"]

KPI_FIELDS = [
    ("net_profit_margin_pct", "Net Profit Margin (%)"),
    ("operating_profit_margin_pct", "Operating Profit Margin (%)"),
    ("return_on_equity_pct", "Return on Equity (%)"),
    ("return_on_capital_employed_pct", "Return on Capital Employed (%)"),
    ("return_on_assets_pct", "Return on Assets (%)"),
    ("debt_to_equity", "Debt / Equity"),
    ("interest_coverage", "Interest Coverage Ratio"),
    ("icr_label", "ICR Label"),
    ("net_debt_cr", "Net Debt (Cr)"),
    ("asset_turnover", "Asset Turnover"),
    ("free_cash_flow_cr", "Free Cash Flow (Cr)"),
    ("capex_intensity_label", "CapEx Intensity"),
    ("fcf_conversion_rate", "FCF Conversion Rate"),
    ("cfo_quality_score", "CFO Quality Score"),
    ("capital_allocation_pattern", "Capital Allocation Pattern"),
    ("revenue_cagr_3yr", "Revenue CAGR 3yr (%)"),
    ("revenue_cagr_5yr", "Revenue CAGR 5yr (%)"),
    ("revenue_cagr_5yr_flag", "Revenue CAGR 5yr Flag"),
    ("pat_cagr_5yr", "PAT CAGR 5yr (%)"),
    ("eps_cagr_5yr", "EPS CAGR 5yr (%)"),
    ("composite_quality_score", "Composite Quality Score"),
]


def _fmt(val: object) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def run(db_path: Path = config.DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        for ticker in DEMO_COMPANIES:
            # Check if company exists
            co = conn.execute(
                "SELECT company_name FROM companies WHERE id = ?", (ticker,)
            ).fetchone()
            if not co:
                print(f"\n{'='*60}")
                print(f"Company not found: {ticker}")
                continue

            # Latest year with KPI data
            row = conn.execute(
                """
                SELECT * FROM financial_ratios
                WHERE company_id = ?
                  AND return_on_equity_pct IS NOT NULL
                ORDER BY year DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()

            print(f"\n{'='*60}")
            print(
                f"  {co['company_name']}  ({ticker})  —  FY{int(row['year']) if row else 'N/A'}"
            )
            print(f"{'='*60}")

            if not row:
                print("  No KPI data available.")
                continue

            for field, label in KPI_FIELDS:
                val = row[field] if field in row.keys() else None
                print(f"  {label:<38}  {_fmt(val):>12}")

    # ── Screener Preview ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  SCREENER: ROE > 15% AND D/E < 1")
    print(f"{'='*60}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        screener_rows = conn.execute(
            """
            SELECT fr.company_id,
                   c.company_name,
                   fr.year,
                   fr.return_on_equity_pct,
                   fr.debt_to_equity
            FROM   financial_ratios fr
            JOIN   companies c ON fr.company_id = c.id
            WHERE  fr.year = (
                       SELECT MAX(year) FROM financial_ratios
                       WHERE company_id = fr.company_id
                         AND return_on_equity_pct IS NOT NULL
                   )
              AND  fr.return_on_equity_pct > 15.0
              AND  fr.debt_to_equity < 1.0
              AND  fr.debt_to_equity IS NOT NULL
            ORDER  BY fr.return_on_equity_pct DESC
            """
        ).fetchall()

    print(f"\n  {'Ticker':<14} {'Company':<30} {'ROE%':>8} {'D/E':>8}")
    print(f"  {'-'*62}")
    for r in screener_rows:
        print(
            f"  {r['company_id']:<14} {r['company_name']:<30} "
            f"{r['return_on_equity_pct']:>7.1f}%  {r['debt_to_equity']:>7.2f}"
        )
    print(f"\n  → {len(screener_rows)} companies match (target: 15–50)")


if __name__ == "__main__":
    run()
