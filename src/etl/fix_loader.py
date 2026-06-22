"""
src/etl/fix_loader.py
---------------------
Targeted re-load utility for ERROR or SKIPPED files from load_audit.csv.

Tries: alt sheet names, alt encodings, skip-rows variants.
Writes output/fix_audit.csv.

Usage:  python src/etl/fix_loader.py  |  make fix
"""

from __future__ import annotations

import csv
import sqlite3
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

import sys
BASE_DIR: Path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

import config as cfg
from src.etl.loader import (
    SOURCE_FILES, DATA_RAW_DIR, DB_PATH, OUTPUT_DIR,
    _normalise_columns, apply_normalisations, load_table,
)

AUDIT_IN  = OUTPUT_DIR / "load_audit.csv"
AUDIT_OUT = OUTPUT_DIR / "fix_audit.csv"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logger.add(OUTPUT_DIR / "pipeline.log", rotation="10 MB",
           level="DEBUG", encoding="utf-8", enqueue=True)

ALT_SHEETS    = ["Sheet1", "Sheet2", "Sheet 1", "Data", "data", "Report"]
ALT_ENCODINGS = ["utf-8", "latin-1", "cp1252", "utf-8-sig"]
ALT_SKIPROWS  = [0, 1, 2]

_FILE_MAP = {e["filename"]: e for e in SOURCE_FILES}


def _try_read_xlsx(path: Path) -> Optional[pd.DataFrame]:
    for skiprows in ALT_SKIPROWS:
        try:
            df = pd.read_excel(path, engine="openpyxl", skiprows=skiprows)
            if len(df) > 0:
                return df
        except Exception:
            pass
        for sheet in ALT_SHEETS:
            try:
                df = pd.read_excel(path, sheet_name=sheet,
                                   engine="openpyxl", skiprows=skiprows)
                if len(df) > 0:
                    logger.debug(f"  sheet='{sheet}' skiprows={skiprows} worked")
                    return df
            except Exception:
                pass
    return None


def _try_read_csv(path: Path) -> Optional[pd.DataFrame]:
    for enc in ALT_ENCODINGS:
        for skiprows in ALT_SKIPROWS:
            try:
                df = pd.read_csv(path, encoding=enc,
                                 skiprows=skiprows if skiprows else None,
                                 low_memory=False)
                if len(df) > 0:
                    logger.debug(f"  enc={enc} skiprows={skiprows} worked")
                    return df
            except Exception:
                pass
    return None


def _read_with_fallbacks(path: Path) -> Optional[pd.DataFrame]:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return _try_read_xlsx(path)
    elif suffix == ".csv":
        return _try_read_csv(path)
    return None


def run_fixes() -> None:
    if not AUDIT_IN.exists():
        print(f"\n⚠️  {AUDIT_IN} not found — run `make load` first.\n")
        return

    with AUDIT_IN.open(encoding="utf-8") as f:
        audit_rows = list(csv.DictReader(f))

    problems = [r for r in audit_rows
                if r.get("status", "").startswith(("error", "skipped"))]

    print(f"\n  load_audit.csv: {len(audit_rows)} entries, {len(problems)} problem(s)\n")

    if not problems:
        print("  ✅  No ERROR or SKIPPED entries — nothing to fix.\n")
        return

    fix_records: list[dict] = []
    conn = sqlite3.connect(DB_PATH) if DB_PATH.exists() else None

    sep = "=" * 62
    print(sep)
    print(f"  {'Filename':<35}  {'Outcome':<12}  Rows")
    print(sep)

    for audit_row in problems:
        filename  = audit_row["filename"]
        table     = audit_row["table"]
        load_type = audit_row["type"]
        file_path = DATA_RAW_DIR / filename
        ts = datetime.now().isoformat(timespec="seconds")

        record = dict(filename=filename, table=table, type=load_type,
                      status="still_missing", rows_loaded=0,
                      rows_rejected=0, timestamp=ts, error="")

        if not file_path.exists():
            print(f"  {filename:<35}  MISSING")
            fix_records.append(record)
            continue

        try:
            df = _read_with_fallbacks(file_path)
            if df is None or len(df) == 0:
                raise ValueError("All read strategies returned 0 rows")

            entry = _FILE_MAP.get(filename, {})
            df = _normalise_columns(df)
            df, rejected = apply_normalisations(
                df, entry.get("year_cols", []), entry.get("ticker_cols", []))

            if conn is None:
                raise RuntimeError("DB not found — run make schema first")

            loaded = load_table(df, table, load_type, conn)
            record.update(status="fixed", rows_loaded=loaded,
                          rows_rejected=rejected,
                          timestamp=datetime.now().isoformat(timespec="seconds"))
            logger.success(f"✅ {filename}: fixed — {loaded} rows")
            print(f"  {filename:<35}  FIXED         {loaded}")

        except Exception as exc:
            record.update(status="fix_failed", error=str(exc))
            logger.error(f"❌ {filename}: {exc}")
            print(f"  {filename:<35}  FIX_FAILED    {str(exc):.35}")

        fix_records.append(record)

    print(sep)
    if conn:
        conn.close()

    fieldnames = ["filename", "table", "type", "status",
                  "rows_loaded", "rows_rejected", "timestamp", "error"]
    with AUDIT_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(fix_records)

    fixed = sum(1 for r in fix_records if r["status"] == "fixed")
    print(f"\n  Fixed {fixed}/{len(fix_records)} problem(s)")
    print(f"  Fix audit → {AUDIT_OUT}\n")
    logger.info(f"Fix audit written → {AUDIT_OUT}")


if __name__ == "__main__":
    run_fixes()
