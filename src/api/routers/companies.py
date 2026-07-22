import sqlite3
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/companies", tags=["Companies"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
TEARSHEETS_DIR = PROJECT_ROOT / "reports" / "tearsheets"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def list_companies(
    sector: Optional[str] = Query(None, description="Filter by broad sector"),
    market_cap_category: Optional[str] = Query(
        None, description="Filter by market cap category"
    ),
    search: Optional[str] = Query(
        None, description="Search term for company name or ticker"
    ),
):
    """List all Nifty 100 companies with optional sector and search filters."""
    conn = get_db()
    query = """
        SELECT c.id as company_id, c.company_name, s.broad_sector, s.sub_sector,
               fr.return_on_equity_pct as roe_pct, fr.return_on_capital_employed_pct as roce_pct,
               fr.market_cap_crore
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN financial_ratios fr ON c.id = fr.company_id AND fr.year = (SELECT MAX(year) FROM financial_ratios)
        WHERE 1=1
    """
    params = []
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    if search:
        query += " AND (c.id LIKE ? OR c.company_name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY c.company_name ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    return {"count": len(results), "companies": results}


@router.get("/{ticker}")
def get_company_profile(ticker: str):
    """Fetch full company profile and latest financial KPIs for a ticker."""
    conn = get_db()
    company = conn.execute(
        """
        SELECT c.*, s.broad_sector, s.sub_sector
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE c.id = ?
    """,
        (ticker,),
    ).fetchone()

    if not company:
        conn.close()
        raise HTTPException(
            status_code=404, detail=f"Company with ticker '{ticker}' not found."
        )

    ratios = conn.execute(
        "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    conn.close()

    res = dict(company)
    res["latest_kpis"] = dict(ratios) if ratios else {}
    return res


@router.get("/{ticker}/pl")
def get_company_pl(
    ticker: str,
    from_year: Optional[int] = Query(None),
    to_year: Optional[int] = Query(None),
):
    """Fetch P&L history for a ticker."""
    conn = get_db()
    query = "SELECT * FROM profitandloss WHERE company_id = ?"
    params = [ticker]
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
    query += " ORDER BY year ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404, detail=f"No P&L data found for '{ticker}'."
        )
    return {"ticker": ticker, "pl": [dict(r) for r in rows]}


@router.get("/{ticker}/bs")
def get_company_bs(
    ticker: str,
    from_year: Optional[int] = Query(None),
    to_year: Optional[int] = Query(None),
):
    """Fetch Balance Sheet history for a ticker."""
    conn = get_db()
    query = "SELECT * FROM balancesheet WHERE company_id = ?"
    params = [ticker]
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
    query += " ORDER BY year ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No Balance Sheet data found for '{ticker}'.",
        )
    return {"ticker": ticker, "bs": [dict(r) for r in rows]}


@router.get("/{ticker}/cashflow")
def get_company_cashflow(
    ticker: str,
    from_year: Optional[int] = Query(None),
    to_year: Optional[int] = Query(None),
):
    """Fetch Cash Flow history for a ticker."""
    conn = get_db()
    query = "SELECT * FROM cashflow WHERE company_id = ?"
    params = [ticker]
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
    query += " ORDER BY year ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404, detail=f"No Cash Flow data found for '{ticker}'."
        )
    return {"ticker": ticker, "cashflow": [dict(r) for r in rows]}


@router.get("/{ticker}/ratios")
def get_company_ratios(ticker: str, year: Optional[int] = Query(None)):
    """Fetch computed financial ratios history for a ticker."""
    conn = get_db()
    query = "SELECT * FROM financial_ratios WHERE company_id = ?"
    params = [ticker]
    if year:
        query += " AND year = ?"
        params.append(year)
    query += " ORDER BY year ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404, detail=f"No ratio data found for '{ticker}'."
        )
    return {"ticker": ticker, "ratios": [dict(r) for r in rows]}


@router.get("/{ticker}/tearsheet")
def get_company_tearsheet_pdf(ticker: str):
    """Return pre-generated PDF tearsheet as a binary download."""
    pdf_file = TEARSHEETS_DIR / f"{ticker}_tearsheet.pdf"
    if not pdf_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Tearsheet PDF for ticker '{ticker}' not found.",
        )
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=f"{ticker}_tearsheet.pdf",
    )
