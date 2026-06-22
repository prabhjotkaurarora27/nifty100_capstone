"""
db/init_db.py
-------------
Initialise (or re-initialise) the Nifty 100 SQLite database from db/schema.sql.

Usage
-----
    python db/init_db.py
    make schema
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# ── project root = parent of db/ ──────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

import config as cfg

# ── paths ──────────────────────────────────────────────────────────────────────
DB_PATH: Path     = cfg.DB_PATH
SCHEMA_FILE: Path = BASE_DIR / "db" / "schema.sql"

# ── expected tables (creation order) ──────────────────────────────────────────
EXPECTED_TABLES: list[str] = [
    "sectors",
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios",
    "analysis",
    "stock_prices",
    "documents",
    "prosandcons",
    "peer_groups",
]


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return {r[0] for r in rows}


def _existing_views(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    ).fetchall()
    return {r[0] for r in rows}


def _existing_indexes(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def init_db(db_path: Path = DB_PATH, schema_file: Path = SCHEMA_FILE) -> None:
    """Create the database and execute the schema SQL."""

    if not schema_file.exists():
        print(f"❌  Schema file not found: {schema_file}")
        sys.exit(1)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = schema_file.read_text(encoding="utf-8")

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def verify_db(db_path: Path = DB_PATH) -> bool:
    """Verify tables, views, indexes, and FK integrity. Returns True if all OK."""

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    tables  = _existing_tables(conn)
    views   = _existing_views(conn)
    indexes = _existing_indexes(conn)

    # ── table status ──────────────────────────────────────────────────────────
    col_w = max(len(t) for t in EXPECTED_TABLES) + 4
    print()
    print("=" * (col_w + 22))
    print(f"  {'Table':<{col_w}}  {'Status':<10}  {'Rows':>6}")
    print("=" * (col_w + 22))

    all_ok = True
    for tbl in EXPECTED_TABLES:
        if tbl in tables:
            (cnt,) = conn.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()
            status = "✅  EXISTS"
        else:
            cnt    = "-"
            status = "❌  MISSING"
            all_ok = False
        print(f"  {tbl:<{col_w}}  {status:<10}  {str(cnt):>6}")

    print("=" * (col_w + 22))

    # ── views ─────────────────────────────────────────────────────────────────
    expected_views = {"v_company_summary", "v_financial_overview", "v_peer_comparison"}
    print(f"\n  Views ({len(views)} found):")
    for v in sorted(expected_views):
        icon = "✅" if v in views else "❌"
        print(f"    {icon}  {v}")

    # ── indexes ───────────────────────────────────────────────────────────────
    print(f"\n  Indexes ({len(indexes)} found):")
    for ix in indexes:
        print(f"      •  {ix}")

    # ── FK integrity check ────────────────────────────────────────────────────
    fk_rows = conn.execute("PRAGMA foreign_key_check;").fetchall()
    print()
    if fk_rows:
        print(f"  ❌  PRAGMA foreign_key_check: {len(fk_rows)} violation(s)")
        for row in fk_rows:
            print(f"       {row}")
        all_ok = False
    else:
        print("  ✅  PRAGMA foreign_key_check: no violations")

    conn.close()

    print()
    if all_ok:
        print("  🎉  Database initialised successfully.")
    else:
        print("  ⚠️   Some checks failed — review above.")
    print()

    return all_ok


if __name__ == "__main__":
    print(f"\n  DB path    : {DB_PATH}")
    print(f"  Schema     : {SCHEMA_FILE}")

    print("\n  Running schema.sql …")
    init_db()
    print("  Schema executed ✅")

    ok = verify_db()
    sys.exit(0 if ok else 1)
