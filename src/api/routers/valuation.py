import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="", tags=["Valuation"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


@router.get("/market-cap/{ticker}")
def get_valuation_history(ticker: str):
    """Fetch historical valuation multiples (P/E, P/B, EV/EBITDA, Dividend Yield) for 2019–2024."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT year, market_cap_crore, pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year ASC
    """
    rows = conn.execute(query, (ticker,)).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Valuation history for ticker '{ticker}' not found.",
        )

    return {"ticker": ticker, "valuation_history": [dict(r) for r in rows]}
