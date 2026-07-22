import sqlite3
import time
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
START_TIME = time.time()


@router.get("")
def get_health():
    """Returns system health, database row counts, uptime, and API version."""
    conn = sqlite3.connect(str(DB_PATH))
    tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "sectors",
        "peer_groups",
        "peer_percentiles",
        "prosandcons",
        "documents",
    ]

    row_counts = {}
    for t in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            row_counts[t] = count
        except Exception:
            row_counts[t] = 0

    conn.close()

    uptime = round(time.time() - START_TIME, 2)

    return {
        "status": "ok",
        "uptime_seconds": uptime,
        "version": "6.0.0",
        "db_row_counts": row_counts,
    }
