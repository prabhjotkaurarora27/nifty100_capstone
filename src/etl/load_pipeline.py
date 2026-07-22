"""
src/etl/load_pipeline.py
------------------------
Day-5 orchestrator: reset DB → load all 12 source files → verify row counts → FK check.

Usage
-----
    python src/etl/load_pipeline.py
    make load
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from loguru import logger

# ── project root ──────────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import config as cfg
from db.init_db import init_db
from src.etl.loader import SOURCE_FILES, DATA_RAW_DIR, run_pipeline

# ── logging ───────────────────────────────────────────────────────────────────
cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logger.add(
    cfg.OUTPUT_DIR / "pipeline.log",
    rotation="10 MB",
    level="DEBUG",
    encoding="utf-8",
    enqueue=True,
)

# ── verification spec ─────────────────────────────────────────────────────────
# (table, expected_rows, exact_match)  exact=True → ==, False → within ±10%
CHECKS: list[tuple[str, int, bool]] = [
    ("companies", 92, True),
    ("profitandloss", 1276, False),
    ("balancesheet", 1312, False),
    ("cashflow", 1187, False),
    ("stock_prices", 5520, True),
]


# ── helpers ────────────────────────────────────────────────────────────────────


def _print_separator(width: int = 62) -> None:
    print("=" * width)


def _scan_missing_files() -> list[str]:
    """Report files listed in SOURCE_FILES that are absent from data/raw/."""
    missing = []
    for entry in SOURCE_FILES:
        path = DATA_RAW_DIR / entry["filename"]
        if not path.exists():
            missing.append(entry["filename"])
            logger.warning(f"Source file not found (will skip): {path}")
    return missing


def _run_row_count_checks(conn: sqlite3.Connection) -> bool:
    """
    Query each expected table, compare against spec.
    Returns True if all CRITICAL checks pass.
    """
    col_w = 18
    _print_separator()
    print(
        f"  {'Table':<{col_w}}  {'Expected':>9}  {'Got':>9}  {'Tolerance':<12}  Result"
    )
    _print_separator()

    all_pass = True
    for table, expected, exact in CHECKS:
        try:
            (got,) = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
        except Exception:
            got = 0

        if exact:
            ok = got == expected
            tol_str = "exact"
        else:
            lo = int(expected * 0.90)
            hi = int(expected * 1.10)
            ok = lo <= got <= hi
            tol_str = "±10%"

        flag = "✅ PASS" if ok else "❌ FAIL"
        if not ok:
            all_pass = False
        print(f"  {table:<{col_w}}  {expected:>9}  {got:>9}  {tol_str:<12}  {flag}")

    _print_separator()
    return all_pass


def _run_fk_check(conn: sqlite3.Connection) -> bool:
    """Run PRAGMA foreign_key_check. Returns True if 0 violations."""
    conn.execute("PRAGMA foreign_keys = ON;")
    rows = conn.execute("PRAGMA foreign_key_check;").fetchall()
    if rows:
        logger.error(f"FK violations: {rows}")
        print(f"  ❌ PRAGMA foreign_key_check: {len(rows)} violation(s)")
        for row in rows:
            print(f"     {row}")
        return False
    print("  ✅ PRAGMA foreign_key_check: 0 violations")
    return True


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print()
    _print_separator()
    print("  Nifty 100 — Full Load Pipeline  (Day 5)")
    _print_separator()

    # ── Step 1: scan source files ─────────────────────────────────────────────
    print("\n📂  Scanning data/raw/ …")
    missing = _scan_missing_files()
    present = len(SOURCE_FILES) - len(missing)
    print(
        f"    {present}/{len(SOURCE_FILES)} source files found"
        + (f"  ⚠️  {len(missing)} missing" if missing else "  ✅")
    )
    for m in missing:
        print(f"    ⚠️   SKIPPED: {m}")

    # ── Step 2: reset DB (drop + recreate schema) ─────────────────────────────
    print("\n🗄️   Resetting database …")
    if cfg.DB_PATH.exists():
        cfg.DB_PATH.unlink()
        logger.info(f"Dropped existing DB: {cfg.DB_PATH}")
    init_db(cfg.DB_PATH, BASE_DIR / "db" / "schema.sql")
    logger.info("Schema recreated ✅")
    print("    Schema recreated ✅")

    # ── Step 3: run ETL loader ────────────────────────────────────────────────
    print("\n⚙️   Running ETL loader …\n")
    try:
        run_pipeline()
    except Exception as exc:
        logger.error(f"Loader raised an exception: {exc}")
        print(f"\n❌  Loader failed: {exc}")
        sys.exit(1)

    # ── Step 4: row-count verification ───────────────────────────────────────
    print("\n📊  Row-count verification:")
    conn = sqlite3.connect(cfg.DB_PATH)
    try:
        counts_ok = _run_row_count_checks(conn)
        print()
        fk_ok = _run_fk_check(conn)
    finally:
        conn.close()

    # ── Step 5: final summary ─────────────────────────────────────────────────
    print()
    _print_separator()
    if counts_ok and fk_ok:
        print("  🎉  Pipeline complete — all checks PASSED")
        logger.success("Day-5 pipeline: ALL CHECKS PASSED")
    else:
        print("  ⚠️   Pipeline complete — some checks FAILED (see above)")
        logger.error("Day-5 pipeline: SOME CHECKS FAILED")
    _print_separator()
    print(f"\n  Audit log : {cfg.OUTPUT_DIR / 'load_audit.csv'}")
    print(f"  DB path   : {cfg.DB_PATH}")
    print()

    sys.exit(0 if (counts_ok and fk_ok) else 1)


if __name__ == "__main__":
    main()
