"""
src/etl/manual_review.py
------------------------
Day-6 manual DQ review script.

- Samples 5 random companies and prints detailed review cards
- Lists all companies with < 5 years P&L coverage
- Checks for CRITICAL failures in validation_failures.csv
- Writes output/manual_review_report.txt
- Prints final summary

Usage
-----
    python src/etl/manual_review.py
    make review
"""

from __future__ import annotations

import csv
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from loguru import logger

# ── project root ───────────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import config as cfg

DB_PATH = cfg.DB_PATH
OUTPUT_DIR = cfg.OUTPUT_DIR
FAILURES_CSV = OUTPUT_DIR / "validation_failures.csv"
REVIEW_REPORT = OUTPUT_DIR / "manual_review_report.txt"
MIN_YEAR_COVERAGE = cfg.DQ_MIN_YEAR_COVERAGE  # default 3; review uses 5

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logger.add(
    OUTPUT_DIR / "pipeline.log",
    rotation="10 MB",
    level="DEBUG",
    encoding="utf-8",
    enqueue=True,
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def _load_failures() -> dict[str, list[dict]]:
    """Load validation_failures.csv grouped by company_id."""
    by_company: dict[str, list[dict]] = defaultdict(list)
    if not FAILURES_CSV.exists():
        return by_company
    with FAILURES_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row.get("company_id", "")
            by_company[cid].append(row)
    return by_company


def _count_critical(failures_map: dict[str, list[dict]]) -> int:
    return sum(
        1
        for rows in failures_map.values()
        for r in rows
        if r.get("severity") == "CRITICAL"
    )


def _company_status(company_failures: list[dict], pl_years: int) -> str:
    """Derive PASS / WARN / FAIL from failures + year coverage."""
    if not company_failures and pl_years >= 5:
        return "PASS"
    has_critical = any(r.get("severity") == "CRITICAL" for r in company_failures)
    if has_critical or pl_years == 0:
        return "FAIL"
    return "WARN"


# ── review card builder ────────────────────────────────────────────────────────


def _build_card(
    conn: sqlite3.Connection, company_id: str, failures_map: dict[str, list[dict]]
) -> tuple[str, str]:
    """Return (card_text, status) for one company."""
    lines = []

    # ── company header ─────────────────────────────────────────────────────────
    row = conn.execute(
        "SELECT name, ticker, bse_code, "
        "(SELECT sector_name FROM sectors WHERE sector_id = c.sector_id) "
        "FROM companies c WHERE company_id = ?",
        (company_id,),
    ).fetchone()

    if not row:
        return f"  [ERROR] company_id '{company_id}' not found\n", "FAIL"

    name, ticker, bse, sector = row
    sector = sector or "Unknown"

    lines += [
        "─" * 60,
        f"  Company  : {name}",
        f"  Ticker   : {ticker}   BSE: {bse}   Sector: {sector}",
        "─" * 60,
    ]

    # ── P&L coverage ──────────────────────────────────────────────────────────
    if _table_exists(conn, "profitandloss"):
        pl_rows = conn.execute(
            "SELECT year FROM profitandloss WHERE company_id = ? ORDER BY year",
            (company_id,),
        ).fetchall()
        pl_years = [r[0] for r in pl_rows]
        pl_count = len(pl_years)
        year_span = f"{pl_years[0]}–{pl_years[-1]}" if pl_years else "—"
    else:
        pl_years, pl_count, year_span = [], 0, "—"

    lines.append(
        f"  P&L Coverage   : {pl_count} year(s)  [{year_span}]"
        + ("  ⚠️  <5 years" if pl_count < 5 else "  ✅")
    )

    # ── balance sheet coverage ─────────────────────────────────────────────────
    if _table_exists(conn, "balancesheet"):
        bs_count = conn.execute(
            "SELECT COUNT(DISTINCT year) FROM balancesheet WHERE company_id = ?",
            (company_id,),
        ).fetchone()[0]
    else:
        bs_count = 0
    lines.append(
        f"  BS  Coverage   : {bs_count} year(s)"
        + ("  ⚠️  <5 years" if bs_count < 5 else "  ✅")
    )

    # ── latest-year financials ─────────────────────────────────────────────────
    if _table_exists(conn, "profitandloss") and pl_years:
        latest = pl_years[-1]
        fin = conn.execute(
            "SELECT revenue, net_profit, opm_percent FROM profitandloss "
            "WHERE company_id = ? AND year = ?",
            (company_id, latest),
        ).fetchone()
        if fin:
            rev, np_, opm = fin
            lines += [
                f"  Latest Year    : {latest}",
                (
                    f"  Revenue        : {rev:>12.2f} Cr"
                    if rev is not None
                    else "  Revenue        : —"
                ),
                (
                    f"  Net Profit     : {np_:>12.2f} Cr"
                    if np_ is not None
                    else "  Net Profit     : —"
                ),
                (
                    f"  OPM %          : {opm:>12.2f} %"
                    if opm is not None
                    else "  OPM %          : —"
                ),
            ]
        else:
            lines.append(f"  Latest Year    : {latest}  (no financial data)")
    else:
        lines.append("  Financials     : — (no P&L data)")

    # ── DQ flags ──────────────────────────────────────────────────────────────
    company_failures = failures_map.get(company_id, [])
    if company_failures:
        lines.append(f"  DQ Flags       : {len(company_failures)}")
        for f in company_failures[:8]:  # show max 8
            icon = "❌" if f["severity"] == "CRITICAL" else "⚠️ "
            lines.append(f"    {icon} [{f['rule_id']}] {f['message'][:70]}")
        if len(company_failures) > 8:
            lines.append(f"    … and {len(company_failures) - 8} more")
    else:
        lines.append("  DQ Flags       : none  ✅")

    status = _company_status(company_failures, pl_count)
    lines.append(f"  Status         : {status}")
    lines.append("")

    return "\n".join(lines) + "\n", status


# ── low-coverage companies ─────────────────────────────────────────────────────


def _low_coverage_companies(conn: sqlite3.Connection) -> list[tuple]:
    """All companies with < 5 distinct years in profitandloss."""
    if not _table_exists(conn, "profitandloss"):
        return []
    return conn.execute(
        "SELECT pl.company_id, c.name, c.ticker, COUNT(DISTINCT pl.year) AS yrs "
        "FROM profitandloss pl "
        "JOIN companies c ON pl.company_id = c.company_id "
        "GROUP BY pl.company_id "
        "HAVING yrs < 5 "
        "ORDER BY yrs ASC, c.name"
    ).fetchall()


# ── main ──────────────────────────────────────────────────────────────────────


def run_review() -> None:
    if not DB_PATH.exists():
        logger.error(f"DB not found: {DB_PATH}")
        print(f"\n❌  DB not found at {DB_PATH}\n   Run: make load\n")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    failures_map = _load_failures()
    critical_count = _count_critical(failures_map)

    # ── pick 5 random companies ───────────────────────────────────────────────
    if not _table_exists(conn, "companies"):
        print("❌  companies table not found — run make load first")
        conn.close()
        sys.exit(1)

    all_ids = [
        r[0] for r in conn.execute("SELECT company_id FROM companies").fetchall()
    ]
    sample_ids = random.sample(all_ids, min(5, len(all_ids)))
    logger.info(f"Sampled {len(sample_ids)} companies: {sample_ids}")

    # ── build report content ──────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 60
    lines = [
        sep,
        "  NIFTY 100 — Manual DQ Review Report",
        f"  Generated : {ts}",
        f"  DB path   : {DB_PATH}",
        f"  Failures  : {FAILURES_CSV.name}"
        + (" (not found)" if not FAILURES_CSV.exists() else ""),
        sep,
        "",
    ]

    # ── CRITICAL alert ────────────────────────────────────────────────────────
    if critical_count:
        lines += [
            f"  ❌  {critical_count} CRITICAL DQ failure(s) found in validation_failures.csv",
            "  Run: make validate  then investigate before signing off.",
            "",
        ]
    else:
        lines += ["  ✅  No CRITICAL DQ failures.", ""]

    # ── 5 random company cards ────────────────────────────────────────────────
    lines.append(f"  SECTION 1 — Random Sample Review ({len(sample_ids)} companies)\n")

    statuses: list[str] = []
    for cid in sample_ids:
        card, status = _build_card(conn, cid, failures_map)
        lines.append(card)
        statuses.append(status)
        # also print to console
        print(card)

    # ── low-coverage companies ────────────────────────────────────────────────
    low_cov = _low_coverage_companies(conn)
    lines += [
        sep,
        f"  SECTION 2 — Companies with < 5 Years P&L Coverage ({len(low_cov)} found)",
        sep,
        "",
    ]
    print(f"\n{'='*60}")
    print(f"  Companies with < 5 years P&L coverage: {len(low_cov)}")
    print(f"{'='*60}")

    if low_cov:
        header = f"  {'Company':<35}  {'Ticker':<12}  {'Years':>5}"
        lines.append(header)
        print(header)
        lines.append("  " + "-" * 55)
        print("  " + "-" * 55)
        for cid, name, ticker, yrs in low_cov:
            row = f"  {name:<35}  {ticker:<12}  {yrs:>5}"
            lines.append(row)
            print(row)
    else:
        lines.append("  ✅  All companies have ≥ 5 years of P&L data.")
        print("  ✅  All companies have ≥ 5 years of P&L data.")
    lines.append("")

    # ── summary ───────────────────────────────────────────────────────────────
    n_pass = statuses.count("PASS")
    n_warn = statuses.count("WARN")
    n_fail = statuses.count("FAIL")

    summary_lines = [
        "",
        sep,
        "  FINAL SUMMARY",
        sep,
        f"  Companies sampled : {len(sample_ids)}",
        f"  PASS              : {n_pass}",
        f"  WARN              : {n_warn}",
        f"  FAIL              : {n_fail}",
        f"  CRITICAL flags    : {critical_count}",
        f"  Low coverage (<5y): {len(low_cov)}",
        sep,
        "",
    ]
    lines += summary_lines
    for sl in summary_lines:
        print(sl)

    conn.close()

    # ── write report ──────────────────────────────────────────────────────────
    REVIEW_REPORT.write_text("\n".join(lines), encoding="utf-8")
    logger.success(f"Review report written → {REVIEW_REPORT}")
    print(f"  Report saved → {REVIEW_REPORT}\n")


if __name__ == "__main__":
    run_review()
