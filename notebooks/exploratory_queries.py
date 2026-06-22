"""
notebooks/exploratory_queries.py
---------------------------------
Runs all 10 exploratory queries against nifty100.db and prints
formatted results using tabulate.

Usage
-----
    python notebooks/exploratory_queries.py
    make explore
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Optional

try:
    from tabulate import tabulate
except ImportError:
    print("tabulate not installed — run: pip install tabulate")
    sys.exit(1)

BASE_DIR: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

import config as cfg

DB_PATH = cfg.DB_PATH

# ── helper ─────────────────────────────────────────────────────────────────────

def _run(conn: sqlite3.Connection, title: str, sql: str,
         limit: int = 10) -> None:
    print(f"\n{'─'*62}")
    print(f"  {title}")
    print(f"{'─'*62}")
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(limit)
        headers = [d[0] for d in cur.description] if cur.description else []
        if rows:
            print(tabulate(rows, headers=headers, tablefmt="rounded_outline",
                           floatfmt=".2f"))
            print(f"  ({len(rows)} row(s) shown)")
        else:
            print("  (no rows returned)")
    except Exception as exc:
        print(f"  ⚠️  Query failed: {exc}")
    print()


# ── queries ────────────────────────────────────────────────────────────────────

QUERIES = [
    (
        "Q1 — Company count by sector",
        """
        SELECT s.sector_name, COUNT(c.company_id) AS company_count
        FROM companies c
        JOIN sectors s ON c.sector_id = s.sector_id
        GROUP BY s.sector_name
        ORDER BY company_count DESC
        """
    ),
    (
        "Q2 — Top 10 companies by revenue (latest year)",
        """
        SELECT c.name, c.ticker, pl.year,
               ROUND(pl.revenue, 2)    AS revenue_cr,
               ROUND(pl.net_profit,2)  AS net_profit_cr,
               ROUND(pl.opm_percent,2) AS opm_pct
        FROM profitandloss pl
        JOIN companies c ON pl.company_id = c.company_id
        WHERE pl.year = (
            SELECT MAX(year) FROM profitandloss
            WHERE company_id = pl.company_id
        )
        ORDER BY pl.revenue DESC
        LIMIT 10
        """
    ),
    (
        "Q3 — Average OPM % by sector (latest year)",
        """
        SELECT s.sector_name,
               COUNT(DISTINCT pl.company_id)  AS companies,
               ROUND(AVG(pl.opm_percent), 2)  AS avg_opm,
               ROUND(MIN(pl.opm_percent), 2)  AS min_opm,
               ROUND(MAX(pl.opm_percent), 2)  AS max_opm
        FROM profitandloss pl
        JOIN companies c ON pl.company_id = c.company_id
        JOIN sectors   s ON c.sector_id   = s.sector_id
        WHERE pl.year = (
            SELECT MAX(year) FROM profitandloss
            WHERE company_id = pl.company_id
        )
        GROUP BY s.sector_name
        ORDER BY avg_opm DESC
        """
    ),
    (
        "Q4 — Companies with < 5 years P&L coverage",
        """
        SELECT c.name, c.ticker,
               COUNT(DISTINCT pl.year) AS years_of_data
        FROM profitandloss pl
        JOIN companies c ON pl.company_id = c.company_id
        GROUP BY pl.company_id
        HAVING years_of_data < 5
        ORDER BY years_of_data ASC
        """
    ),
    (
        "Q5 — YoY revenue growth (first company alphabetically)",
        """
        SELECT curr.year,
               ROUND(curr.revenue, 2)  AS revenue_cr,
               ROUND(prev.revenue, 2)  AS prev_revenue_cr,
               ROUND(
                   (curr.revenue - prev.revenue) * 100.0
                   / NULLIF(prev.revenue, 0), 2
               ) AS yoy_growth_pct
        FROM profitandloss curr
        JOIN profitandloss prev
          ON curr.company_id = prev.company_id
         AND curr.year       = prev.year + 1
        WHERE curr.company_id = (
            SELECT company_id FROM companies ORDER BY name LIMIT 1
        )
        ORDER BY curr.year
        """
    ),
    (
        "Q6 — Debt-to-equity ratio (latest year, top 10 by D/E)",
        """
        SELECT c.name, c.ticker,
               bs.year,
               ROUND(bs.borrowings, 2) AS borrowings_cr,
               ROUND(bs.equity, 2)     AS equity_cr,
               ROUND(bs.borrowings / NULLIF(bs.equity, 0), 2) AS debt_to_equity
        FROM balancesheet bs
        JOIN companies c ON bs.company_id = c.company_id
        WHERE bs.year = (
            SELECT MAX(year) FROM balancesheet
            WHERE company_id = bs.company_id
        )
          AND bs.equity > 0
        ORDER BY debt_to_equity DESC
        LIMIT 10
        """
    ),
    (
        "Q7 — FCF positive companies (latest year)",
        """
        SELECT COUNT(*) AS fcf_positive_companies,
               ROUND(AVG(free_cash_flow), 2) AS avg_fcf_cr,
               ROUND(SUM(free_cash_flow), 2) AS total_fcf_cr
        FROM cashflow cf
        WHERE cf.year = (
            SELECT MAX(year) FROM cashflow
            WHERE company_id = cf.company_id
        )
          AND cf.free_cash_flow > 0
        """
    ),
    (
        "Q8 — Stock price 52-week range (latest year, top 10 by range)",
        """
        SELECT c.name, c.ticker, sp.year,
               ROUND(sp.week_52_high, 2) AS high_52w,
               ROUND(sp.week_52_low,  2) AS low_52w,
               ROUND(sp.close_price,  2) AS close,
               ROUND(sp.week_52_high - sp.week_52_low, 2) AS range_width
        FROM stock_prices sp
        JOIN companies c ON sp.company_id = c.company_id
        WHERE sp.year = (
            SELECT MAX(year) FROM stock_prices
            WHERE company_id = sp.company_id
        )
        ORDER BY range_width DESC
        LIMIT 10
        """
    ),
    (
        "Q9 — Peer group avg P/E by sector",
        """
        SELECT s.sector_name,
               COUNT(DISTINCT pg.company_id) AS companies,
               ROUND(AVG(pg.pe_ratio), 2)    AS avg_peer_pe,
               ROUND(MIN(pg.pe_ratio), 2)    AS min_pe,
               ROUND(MAX(pg.pe_ratio), 2)    AS max_pe
        FROM peer_groups pg
        JOIN sectors s ON pg.sector_id = s.sector_id
        WHERE pg.pe_ratio > 0
        GROUP BY s.sector_name
        ORDER BY avg_peer_pe DESC
        """
    ),
    (
        "Q10 — Data completeness score per company (% tables populated)",
        """
        SELECT c.name, c.ticker,
               CASE WHEN pl.cnt  > 0 THEN 1 ELSE 0 END +
               CASE WHEN bs.cnt  > 0 THEN 1 ELSE 0 END +
               CASE WHEN cf.cnt  > 0 THEN 1 ELSE 0 END +
               CASE WHEN fr.cnt  > 0 THEN 1 ELSE 0 END +
               CASE WHEN sp.cnt  > 0 THEN 1 ELSE 0 END AS tables_populated,
               ROUND(100.0 * (
                   CASE WHEN pl.cnt > 0 THEN 1 ELSE 0 END +
                   CASE WHEN bs.cnt > 0 THEN 1 ELSE 0 END +
                   CASE WHEN cf.cnt > 0 THEN 1 ELSE 0 END +
                   CASE WHEN fr.cnt > 0 THEN 1 ELSE 0 END +
                   CASE WHEN sp.cnt > 0 THEN 1 ELSE 0 END
               ) / 5.0, 1) AS completeness_pct
        FROM companies c
        LEFT JOIN (SELECT company_id, COUNT(*) cnt FROM profitandloss   GROUP BY company_id) pl ON c.company_id = pl.company_id
        LEFT JOIN (SELECT company_id, COUNT(*) cnt FROM balancesheet     GROUP BY company_id) bs ON c.company_id = bs.company_id
        LEFT JOIN (SELECT company_id, COUNT(*) cnt FROM cashflow         GROUP BY company_id) cf ON c.company_id = cf.company_id
        LEFT JOIN (SELECT company_id, COUNT(*) cnt FROM financial_ratios GROUP BY company_id) fr ON c.company_id = fr.company_id
        LEFT JOIN (SELECT company_id, COUNT(*) cnt FROM stock_prices     GROUP BY company_id) sp ON c.company_id = sp.company_id
        ORDER BY completeness_pct DESC
        LIMIT 20
        """
    ),
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"\n❌  DB not found: {DB_PATH}\n   Run: make load\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    print(f"\n{'='*62}")
    print(f"  Nifty 100 — Exploratory Queries  ({len(QUERIES)} queries)")
    print(f"  DB: {DB_PATH}")
    print(f"{'='*62}")

    for title, sql in QUERIES:
        _run(conn, title, sql.strip())

    conn.close()
    print(f"{'='*62}")
    print("  All queries complete.")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
