import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="", tags=["Documents"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


@router.get("/companies/{ticker}/documents")
def get_company_documents(ticker: str):
    """Fetch annual report BSE URLs for a company with validity status."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    query = "SELECT year, annual_report FROM documents WHERE company_id = ? ORDER BY year DESC"
    rows = conn.execute(query, (ticker,)).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No annual report documents found for ticker '{ticker}'.",
        )

    results = []
    for r in rows:
        url = str(r["annual_report"]).strip() if r["annual_report"] else ""
        is_valid = bool(url and url.lower() not in ["nan", "none", "", "null"])
        results.append(
            {
                "year": r["year"],
                "annual_report_url": url,
                "is_url_valid": is_valid,
            }
        )

    return {"ticker": ticker, "documents": results}
