import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/sectors", tags=["Sectors"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


@router.get("")
def list_sectors():
    """List all 11 broad sectors with company counts and sector median KPIs."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT s.broad_sector as sector_name,
               COUNT(DISTINCT c.id) as company_count
        FROM sectors s
        JOIN companies c ON s.company_id = c.id
        WHERE s.broad_sector IS NOT NULL
        GROUP BY s.broad_sector
        ORDER BY company_count DESC
    """
    sectors_rows = conn.execute(query).fetchall()

    results = []
    for r in sectors_rows:
        sec = r["sector_name"]
        count = r["company_count"]

        # Median ratios
        ratios_query = """
            SELECT fr.return_on_equity_pct as roe, fr.pe_ratio as pe, fr.debt_to_equity as de
            FROM financial_ratios fr
            JOIN sectors s ON fr.company_id = s.company_id
            WHERE s.broad_sector = ? AND fr.year = (SELECT MAX(year) FROM financial_ratios)
        """
        ratios_df = conn.execute(ratios_query, (sec,)).fetchall()
        roes = [row["roe"] for row in ratios_df if row["roe"] is not None]
        pes = [row["pe"] for row in ratios_df if row["pe"] is not None]
        des = [row["de"] for row in ratios_df if row["de"] is not None]

        import numpy as np

        med_roe = float(np.median(roes)) if roes else None
        med_pe = float(np.median(pes)) if pes else None
        med_de = float(np.median(des)) if des else None

        results.append(
            {
                "sector_name": sec,
                "company_count": count,
                "median_roe": round(med_roe, 2) if med_roe else None,
                "median_pe": round(med_pe, 2) if med_pe else None,
                "median_de": round(med_de, 2) if med_de else None,
            }
        )

    conn.close()
    return {"count": len(results), "sectors": results}


@router.get("/{sector}/companies")
def get_sector_companies(sector: str):
    """List all companies in a specific broad sector with their latest KPIs."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT c.id as company_id, c.company_name, s.broad_sector, s.sub_sector,
               fr.return_on_equity_pct as roe, fr.return_on_capital_employed_pct as roce,
               fr.debt_to_equity as de, fr.revenue_cagr_5yr, fr.composite_quality_score
        FROM companies c
        JOIN sectors s ON c.id = s.company_id
        LEFT JOIN financial_ratios fr ON c.id = fr.company_id AND fr.year = (SELECT MAX(year) FROM financial_ratios)
        WHERE s.broad_sector = ?
        ORDER BY fr.composite_quality_score DESC
    """
    rows = conn.execute(query, (sector,)).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404, detail=f"Broad sector '{sector}' not found."
        )

    return {"sector": sector, "count": len(rows), "companies": [dict(r) for r in rows]}
