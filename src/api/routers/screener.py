import sqlite3
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/screener", tags=["Screener"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


@router.get("")
def run_screener_api(
    min_roe: Optional[float] = Query(None, description="Minimum ROE (%)"),
    max_de: Optional[float] = Query(None, description="Maximum Debt-to-Equity"),
    min_fcf: Optional[float] = Query(None, description="Minimum Free Cash Flow (Cr)"),
    sector: Optional[str] = Query(None, description="Filter by broad sector"),
    min_rev_cagr_5yr: Optional[float] = Query(
        None, description="Minimum 5yr Revenue CAGR (%)"
    ),
    min_pat_cagr_5yr: Optional[float] = Query(
        None, description="Minimum 5yr PAT CAGR (%)"
    ),
    max_pe: Optional[float] = Query(None, description="Maximum P/E Ratio"),
):
    """Executes multi-parameter screener query and returns ranked company results."""
    # Parameter Validation (HTTP 400 for invalid values)
    if max_pe is not None and max_pe < 0:
        raise HTTPException(status_code=400, detail="max_pe cannot be negative.")
    if max_de is not None and max_de < 0:
        raise HTTPException(status_code=400, detail="max_de cannot be negative.")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT fr.company_id, c.company_name, s.broad_sector as sector,
               fr.composite_quality_score, fr.return_on_equity_pct as roe,
               fr.debt_to_equity as de, fr.free_cash_flow_cr as fcf,
               fr.revenue_cagr_5yr, fr.pat_cagr_5yr, fr.pe_ratio as pe
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE fr.year = (SELECT MAX(year) FROM financial_ratios)
    """
    params = []

    if min_roe is not None:
        query += " AND fr.return_on_equity_pct >= ?"
        params.append(min_roe)
    if max_de is not None:
        # Financials sector auto-skip
        query += " AND (s.broad_sector = 'Financials' OR fr.debt_to_equity <= ?)"
        params.append(max_de)
    if min_fcf is not None:
        query += " AND fr.free_cash_flow_cr >= ?"
        params.append(min_fcf)
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    if min_rev_cagr_5yr is not None:
        query += " AND fr.revenue_cagr_5yr >= ?"
        params.append(min_rev_cagr_5yr)
    if min_pat_cagr_5yr is not None:
        query += " AND fr.pat_cagr_5yr >= ?"
        params.append(min_pat_cagr_5yr)
    if max_pe is not None:
        query += " AND fr.pe_ratio IS NOT NULL AND fr.pe_ratio <= ?"
        params.append(max_pe)

    query += " ORDER BY fr.composite_quality_score DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    return {"count": len(results), "results": results}
