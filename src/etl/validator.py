"""
src/etl/validator.py
--------------------
16 Data-Quality rules for the Nifty 100 pipeline.

Usage
-----
    python src/etl/validator.py
"""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from loguru import logger

# ── Project root & config ──────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import config as cfg

OUTPUT_DIR: Path = cfg.OUTPUT_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FAILURES_FILE: Path = OUTPUT_DIR / "validation_failures.csv"

# ── Logging ────────────────────────────────────────────────────────────────────
logger.add(
    OUTPUT_DIR / "pipeline.log", rotation="10 MB", level="DEBUG", encoding="utf-8"
)

# ── Failure dict helper ────────────────────────────────────────────────────────


def _f(
    rule_id: str,
    severity: str,
    table: str,
    message: str,
    company_id: Any = None,
    year: Any = None,
    field: str = "",
    observed_value: Any = None,
    expected_value: Any = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "table": table,
        "company_id": company_id,
        "year": year,
        "field": field,
        "observed_value": observed_value,
        "expected_value": expected_value,
        "message": message,
    }


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info([{table}])")
    return {row[1].lower() for row in cur.fetchall()}


# ══════════════════════════════════════════════════════════════════════════════
# DQ RULES
# ══════════════════════════════════════════════════════════════════════════════


def check_dq01(conn: sqlite3.Connection) -> list[dict]:
    """DQ-01 CRITICAL – PK uniqueness on companies.id / company_id"""
    failures = []
    if not _table_exists(conn, "companies"):
        return failures
    pk_col = "id" if "id" in _columns(conn, "companies") else "company_id"
    rows = conn.execute(
        f"SELECT {pk_col}, COUNT(*) c FROM companies GROUP BY {pk_col} HAVING c > 1"
    ).fetchall()
    for cid, cnt in rows:
        failures.append(
            _f(
                "DQ-01",
                "CRITICAL",
                "companies",
                f"Duplicate company_id '{cid}' appears {cnt} times",
                company_id=cid,
                field=pk_col,
                observed_value=cnt,
                expected_value=1,
            )
        )
    return failures


def check_dq02(conn: sqlite3.Connection) -> list[dict]:
    """DQ-02 CRITICAL – Composite PK uniqueness (company_id, year)"""
    failures = []
    for tbl in ("profitandloss", "balancesheet", "cashflow"):
        if not _table_exists(conn, tbl):
            continue
        cols = _columns(conn, tbl)
        if "company_id" not in cols or "year" not in cols:
            continue
        rows = conn.execute(
            f"SELECT company_id, year, COUNT(*) c FROM [{tbl}] "
            f"GROUP BY company_id, year HAVING c > 1"
        ).fetchall()
        for cid, yr, cnt in rows:
            failures.append(
                _f(
                    "DQ-02",
                    "CRITICAL",
                    tbl,
                    f"Duplicate (company_id={cid}, year={yr}) appears {cnt} times",
                    company_id=cid,
                    year=yr,
                    field="company_id,year",
                    observed_value=cnt,
                    expected_value=1,
                )
            )
    return failures


def check_dq03(conn: sqlite3.Connection) -> list[dict]:
    """DQ-03 CRITICAL – FK integrity: company_id must exist in companies"""
    failures = []
    if not _table_exists(conn, "companies"):
        return failures
    pk_col = "id" if "id" in _columns(conn, "companies") else "company_id"
    child_tables = [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "financial_ratios",
        "stock_prices",
    ]
    for tbl in child_tables:
        if not _table_exists(conn, tbl):
            continue
        if "company_id" not in _columns(conn, tbl):
            continue
        rows = conn.execute(
            f"SELECT DISTINCT t.company_id FROM [{tbl}] t "
            f"LEFT JOIN companies c ON t.company_id = c.{pk_col} "
            f"WHERE c.{pk_col} IS NULL AND t.company_id IS NOT NULL"
        ).fetchall()
        for (cid,) in rows:
            failures.append(
                _f(
                    "DQ-03",
                    "CRITICAL",
                    tbl,
                    f"company_id '{cid}' not found in companies",
                    company_id=cid,
                    field="company_id",
                    observed_value=cid,
                    expected_value="exists in companies",
                )
            )
    return failures


def check_dq04(conn: sqlite3.Connection) -> list[dict]:
    """DQ-04 WARNING – Balance sheet: total_assets ≈ total_liabilities + equity"""
    failures = []
    tbl = "balancesheet"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    needed = {"total_assets", "total_liabilities", "equity"}
    if not needed.issubset(cols):
        return failures
    tol = cfg.DQ_BS_BALANCE_TOLERANCE
    rows = conn.execute(
        f"SELECT company_id, year, total_assets, total_liabilities, equity FROM [{tbl}] "
        f"WHERE total_assets IS NOT NULL AND total_liabilities IS NOT NULL AND equity IS NOT NULL"
    ).fetchall()
    for cid, yr, assets, liab, eq in rows:
        rhs = liab + eq
        if assets == 0:
            continue
        diff = abs(assets - rhs) / abs(assets)
        if diff > tol:
            failures.append(
                _f(
                    "DQ-04",
                    "WARNING",
                    tbl,
                    f"Balance sheet imbalance: assets={assets}, liab+equity={rhs:.2f}",
                    company_id=cid,
                    year=yr,
                    field="total_assets",
                    observed_value=round(diff, 4),
                    expected_value=f"<={tol}",
                )
            )
    return failures


def check_dq05(conn: sqlite3.Connection) -> list[dict]:
    """DQ-05 WARNING – OPM cross-check: operating_profit/revenue within configured range"""
    failures = []
    tbl = "profitandloss"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    if "operating_profit" not in cols or "revenue" not in cols:
        return failures
    rows = conn.execute(
        f"SELECT company_id, year, operating_profit, revenue FROM [{tbl}] "
        f"WHERE revenue IS NOT NULL AND revenue != 0 AND operating_profit IS NOT NULL"
    ).fetchall()
    for cid, yr, op, rev in rows:
        opm = op / rev
        if not (cfg.DQ_OPM_MIN <= opm <= cfg.DQ_OPM_MAX):
            failures.append(
                _f(
                    "DQ-05",
                    "WARNING",
                    tbl,
                    f"OPM {opm:.4f} outside [{cfg.DQ_OPM_MIN}, {cfg.DQ_OPM_MAX}]",
                    company_id=cid,
                    year=yr,
                    field="operating_profit",
                    observed_value=round(opm, 4),
                    expected_value=f"[{cfg.DQ_OPM_MIN},{cfg.DQ_OPM_MAX}]",
                )
            )
    return failures


def check_dq06(conn: sqlite3.Connection) -> list[dict]:
    """DQ-06 WARNING – Positive sales: revenue > 0"""
    failures = []
    tbl = "profitandloss"
    if not _table_exists(conn, tbl):
        return failures
    if "revenue" not in _columns(conn, tbl):
        return failures
    rows = conn.execute(
        f"SELECT company_id, year, revenue FROM [{tbl}] "
        f"WHERE revenue IS NOT NULL AND revenue <= 0"
    ).fetchall()
    for cid, yr, rev in rows:
        failures.append(
            _f(
                "DQ-06",
                "WARNING",
                tbl,
                f"revenue={rev} is not positive",
                company_id=cid,
                year=yr,
                field="revenue",
                observed_value=rev,
                expected_value=">0",
            )
        )
    return failures


def check_dq07(conn: sqlite3.Connection) -> list[dict]:
    """DQ-07 CRITICAL – No null company_id in any table"""
    failures = []
    tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "financial_ratios",
        "stock_prices",
        "sectors",
        "peer_groups",
    ]
    for tbl in tables:
        if not _table_exists(conn, tbl):
            continue
        if "company_id" not in _columns(conn, tbl):
            continue
        (cnt,) = conn.execute(
            f"SELECT COUNT(*) FROM [{tbl}] WHERE company_id IS NULL"
        ).fetchone()
        if cnt:
            failures.append(
                _f(
                    "DQ-07",
                    "CRITICAL",
                    tbl,
                    f"{cnt} rows with NULL company_id",
                    field="company_id",
                    observed_value=cnt,
                    expected_value=0,
                )
            )
    return failures


def check_dq08(conn: sqlite3.Connection) -> list[dict]:
    """DQ-08 CRITICAL – No null year in financial tables"""
    failures = []
    tables = ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]
    for tbl in tables:
        if not _table_exists(conn, tbl):
            continue
        if "year" not in _columns(conn, tbl):
            continue
        (cnt,) = conn.execute(
            f"SELECT COUNT(*) FROM [{tbl}] WHERE year IS NULL"
        ).fetchone()
        if cnt:
            failures.append(
                _f(
                    "DQ-08",
                    "CRITICAL",
                    tbl,
                    f"{cnt} rows with NULL year",
                    field="year",
                    observed_value=cnt,
                    expected_value=0,
                )
            )
    return failures


def check_dq09(conn: sqlite3.Connection) -> list[dict]:
    """DQ-09 WARNING – Net cash: operating+investing+financing ≈ net_cash (within 5%)"""
    failures = []
    tbl = "cashflow"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    needed = {
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
        "net_cash",
    }
    if not needed.issubset(cols):
        return failures
    rows = conn.execute(
        f"SELECT company_id, year, operating_cash_flow, investing_cash_flow, "
        f"financing_cash_flow, net_cash FROM [{tbl}] "
        f"WHERE net_cash IS NOT NULL AND net_cash != 0"
    ).fetchall()
    for cid, yr, op, inv, fin, net in rows:
        if op is None or inv is None or fin is None:
            continue
        computed = op + inv + fin
        diff = abs(computed - net) / abs(net)
        if diff > 0.05:
            failures.append(
                _f(
                    "DQ-09",
                    "WARNING",
                    tbl,
                    f"Net cash mismatch: computed={computed:.2f}, reported={net:.2f}",
                    company_id=cid,
                    year=yr,
                    field="net_cash",
                    observed_value=round(diff, 4),
                    expected_value="<=0.05",
                )
            )
    return failures


def check_dq10(conn: sqlite3.Connection) -> list[dict]:
    """DQ-10 WARNING – Tax rate between 0% and 60%"""
    failures = []
    tbl = "profitandloss"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    if "tax" not in cols or "profit_before_tax" not in cols:
        return failures
    rows = conn.execute(
        f"SELECT company_id, year, tax, profit_before_tax FROM [{tbl}] "
        f"WHERE profit_before_tax IS NOT NULL AND profit_before_tax > 0 "
        f"AND tax IS NOT NULL"
    ).fetchall()
    for cid, yr, tax, pbt in rows:
        rate = tax / pbt
        if not (0.0 <= rate <= 0.60):
            failures.append(
                _f(
                    "DQ-10",
                    "WARNING",
                    tbl,
                    f"Tax rate {rate:.2%} outside [0%, 60%]",
                    company_id=cid,
                    year=yr,
                    field="tax",
                    observed_value=round(rate, 4),
                    expected_value="[0.0,0.6]",
                )
            )
    return failures


def check_dq11(conn: sqlite3.Connection) -> list[dict]:
    """DQ-11 WARNING – Dividend payout ratio ≤ DQ_DIVIDEND_CAP"""
    failures = []
    tbl = "profitandloss"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    if "dividend" not in cols or "net_profit" not in cols:
        return failures
    rows = conn.execute(
        f"SELECT company_id, year, dividend, net_profit FROM [{tbl}] "
        f"WHERE net_profit IS NOT NULL AND net_profit > 0 AND dividend IS NOT NULL"
    ).fetchall()
    cap = cfg.DQ_DIVIDEND_CAP
    for cid, yr, div, np_ in rows:
        ratio = div / np_
        if ratio > cap:
            failures.append(
                _f(
                    "DQ-11",
                    "WARNING",
                    tbl,
                    f"Dividend payout {ratio:.2f} > cap {cap}",
                    company_id=cid,
                    year=yr,
                    field="dividend",
                    observed_value=round(ratio, 4),
                    expected_value=f"<={cap}",
                )
            )
    return failures


def check_dq12(conn: sqlite3.Connection) -> list[dict]:
    """DQ-12 INFO – URL format check on documents table"""
    failures = []
    tbl = "documents"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    url_cols = [c for c in cols if "url" in c or "link" in c]
    if not url_cols:
        return failures
    pattern = re.compile(r"^https?://", re.IGNORECASE)
    for col in url_cols:
        rows = conn.execute(
            f"SELECT company_id, year, [{col}] FROM [{tbl}] WHERE [{col}] IS NOT NULL"
        ).fetchall()
        for cid, yr, url in rows:
            if url and not pattern.match(str(url)):
                failures.append(
                    _f(
                        "DQ-12",
                        "INFO",
                        tbl,
                        f"Invalid URL in column '{col}': {url!r}",
                        company_id=cid,
                        year=yr,
                        field=col,
                        observed_value=url,
                        expected_value="http(s)://...",
                    )
                )
    return failures


def check_dq13(conn: sqlite3.Connection) -> list[dict]:
    """DQ-13 CRITICAL – No duplicate tickers in companies"""
    failures = []
    if not _table_exists(conn, "companies"):
        return failures
    cols = _columns(conn, "companies")
    ticker_col = next(
        (c for c in ("ticker", "symbol", "nse_symbol") if c in cols), None
    )
    if not ticker_col:
        return failures
    rows = conn.execute(
        f"SELECT [{ticker_col}], COUNT(*) c FROM companies "
        f"WHERE [{ticker_col}] IS NOT NULL "
        f"GROUP BY [{ticker_col}] HAVING c > 1"
    ).fetchall()
    for tick, cnt in rows:
        failures.append(
            _f(
                "DQ-13",
                "CRITICAL",
                "companies",
                f"Duplicate ticker '{tick}' appears {cnt} times",
                field=ticker_col,
                observed_value=cnt,
                expected_value=1,
            )
        )
    return failures


def check_dq14(conn: sqlite3.Connection) -> list[dict]:
    """DQ-14 WARNING – EPS sign consistency: net_profit > 0 → eps > 0"""
    failures = []
    tbl = "profitandloss"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    if "net_profit" not in cols or "eps" not in cols:
        return failures
    rows = conn.execute(
        f"SELECT company_id, year, net_profit, eps FROM [{tbl}] "
        f"WHERE net_profit IS NOT NULL AND eps IS NOT NULL AND net_profit > 0 AND eps <= 0"
    ).fetchall()
    for cid, yr, np_, eps in rows:
        failures.append(
            _f(
                "DQ-14",
                "WARNING",
                tbl,
                f"net_profit={np_} > 0 but eps={eps} <= 0",
                company_id=cid,
                year=yr,
                field="eps",
                observed_value=eps,
                expected_value=">0",
            )
        )
    return failures


def check_dq15(conn: sqlite3.Connection) -> list[dict]:
    """DQ-15 WARNING – BSE code: must be 6-digit numeric"""
    failures = []
    if not _table_exists(conn, "companies"):
        return failures
    cols = _columns(conn, "companies")
    bse_col = next((c for c in ("bse_code", "bse", "bse_symbol") if c in cols), None)
    if not bse_col:
        return failures
    pattern = re.compile(r"^\d{6}$")
    rows = conn.execute(
        f"SELECT company_id, [{bse_col}] FROM companies WHERE [{bse_col}] IS NOT NULL"
    ).fetchall()
    for cid, code in rows:
        if not pattern.match(str(code).strip()):
            failures.append(
                _f(
                    "DQ-15",
                    "WARNING",
                    "companies",
                    f"BSE code '{code}' is not 6-digit numeric",
                    company_id=cid,
                    field=bse_col,
                    observed_value=code,
                    expected_value="6-digit numeric",
                )
            )
    return failures


def check_dq16(conn: sqlite3.Connection) -> list[dict]:
    """DQ-16 INFO – Year coverage: each company needs DQ_MIN_YEAR_COVERAGE years of P&L"""
    failures = []
    tbl = "profitandloss"
    if not _table_exists(conn, tbl):
        return failures
    cols = _columns(conn, tbl)
    if "company_id" not in cols or "year" not in cols:
        return failures
    min_cov = cfg.DQ_MIN_YEAR_COVERAGE
    rows = conn.execute(
        f"SELECT company_id, COUNT(DISTINCT year) yrs FROM [{tbl}] "
        f"GROUP BY company_id HAVING yrs < ?",
        (min_cov,),
    ).fetchall()
    for cid, yrs in rows:
        failures.append(
            _f(
                "DQ-16",
                "INFO",
                tbl,
                f"company_id '{cid}' has only {yrs} year(s) of P&L data",
                company_id=cid,
                field="year",
                observed_value=yrs,
                expected_value=f">={min_cov}",
            )
        )
    return failures


# ══════════════════════════════════════════════════════════════════════════════
# Orchestrator
# ══════════════════════════════════════════════════════════════════════════════

_ALL_CHECKS = [
    check_dq01,
    check_dq02,
    check_dq03,
    check_dq04,
    check_dq05,
    check_dq06,
    check_dq07,
    check_dq08,
    check_dq09,
    check_dq10,
    check_dq11,
    check_dq12,
    check_dq13,
    check_dq14,
    check_dq15,
    check_dq16,
]

_FIELDNAMES = [
    "rule_id",
    "severity",
    "table",
    "company_id",
    "year",
    "field",
    "observed_value",
    "expected_value",
    "message",
]


def run_all_checks(conn: sqlite3.Connection) -> list[dict]:
    """Run all 16 DQ rules and return combined failure list."""
    all_failures: list[dict] = []

    for fn in _ALL_CHECKS:
        rule_id = fn.__doc__.split()[0] if fn.__doc__ else fn.__name__
        try:
            failures = fn(conn)
            count = len(failures)
            sev = failures[0]["severity"] if failures else "OK"

            if failures:
                log_fn = (
                    logger.error
                    if sev == "CRITICAL"
                    else (logger.warning if sev == "WARNING" else logger.info)
                )
                log_fn(f"{rule_id}: {count} failure(s)")
            else:
                logger.info(f"{rule_id}: ✅ no failures")

            all_failures.extend(failures)

        except Exception as exc:
            logger.error(f"{rule_id}: check raised exception – {exc}")

    return all_failures


def write_failures(failures: list[dict]) -> None:
    """Write failures to output/validation_failures.csv."""
    FAILURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with FAILURES_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(failures)
    logger.info(
        f"Validation failures written → {FAILURES_FILE}  ({len(failures)} rows)"
    )


def print_summary(failures: list[dict]) -> None:
    """Print a summary table of failures grouped by rule."""
    from collections import defaultdict

    counts: dict[str, dict] = defaultdict(lambda: {"severity": "", "count": 0})
    for f in failures:
        key = f["rule_id"]
        counts[key]["severity"] = f["severity"]
        counts[key]["count"] += 1

    print("\n" + "=" * 52)
    print(f"  {'Rule':<8}  {'Severity':<10}  {'Failures':>8}")
    print("=" * 52)

    for fn in _ALL_CHECKS:
        # extract rule id from docstring
        rid = (fn.__doc__ or "").split()[0] if fn.__doc__ else fn.__name__
        sev_map = {
            "DQ-01": "CRITICAL",
            "DQ-02": "CRITICAL",
            "DQ-03": "CRITICAL",
            "DQ-04": "WARNING",
            "DQ-05": "WARNING",
            "DQ-06": "WARNING",
            "DQ-07": "CRITICAL",
            "DQ-08": "CRITICAL",
            "DQ-09": "WARNING",
            "DQ-10": "WARNING",
            "DQ-11": "WARNING",
            "DQ-12": "INFO",
            "DQ-13": "CRITICAL",
            "DQ-14": "WARNING",
            "DQ-15": "WARNING",
            "DQ-16": "INFO",
        }
        sev = sev_map.get(rid, "")
        cnt = counts[rid]["count"] if rid in counts else 0
        flag = "❌" if cnt and sev == "CRITICAL" else ("⚠️ " if cnt else "✅")
        print(f"  {rid:<8}  {sev:<10}  {cnt:>6}  {flag}")

    total = len(failures)
    critical = sum(1 for f in failures if f["severity"] == "CRITICAL")
    warning = sum(1 for f in failures if f["severity"] == "WARNING")
    info = sum(1 for f in failures if f["severity"] == "INFO")
    print("=" * 52)
    print(
        f"  Total: {total}  |  CRITICAL: {critical}  WARNING: {warning}  INFO: {info}"
    )
    print("=" * 52 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    db_path = cfg.DB_PATH
    if not db_path.exists():
        logger.warning(f"DB not found at {db_path}. Run loader.py first.")
        print(f"\n⚠️  DB not found at: {db_path}")
        print("   Run:  python src/etl/loader.py  to populate the database first.\n")
        sys.exit(0)

    logger.info(f"Connecting to {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        failures = run_all_checks(conn)
    finally:
        conn.close()

    write_failures(failures)
    print_summary(failures)
