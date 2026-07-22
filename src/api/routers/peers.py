import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="", tags=["Peers"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


@router.get("/peers/{group_name}")
def get_peer_group_details(group_name: str):
    """Fetch all member companies and percentile ranks for a specific peer group."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark, c.company_name,
               pp.metric, pp.value, pp.percentile_rank
        FROM peer_groups pg
        JOIN companies c ON pg.company_id = c.id
        LEFT JOIN peer_percentiles pp ON pg.company_id = pp.company_id AND pg.peer_group_name = pp.peer_group_name
        WHERE pg.peer_group_name = ?
        ORDER BY pg.company_id, pp.metric
    """
    rows = conn.execute(query, (group_name,)).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404, detail=f"Peer group '{group_name}' not found."
        )

    results = [dict(r) for r in rows]
    return {"peer_group_name": group_name, "count": len(results), "members": results}


@router.get("/companies/{ticker}/peers/compare")
def compare_company_peers_radar(ticker: str):
    """Fetch 8-metric radar comparative data for a company vs peer group average and benchmark."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Find peer group of ticker
    pg_row = conn.execute(
        "SELECT peer_group_name, is_benchmark FROM peer_groups WHERE company_id = ?",
        (ticker,),
    ).fetchone()

    if not pg_row:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' has no assigned peer group.",
        )

    group_name = pg_row["peer_group_name"]

    # Fetch 8 metrics for ticker
    metrics_query = """
        SELECT company_id, return_on_equity_pct as roe, return_on_capital_employed_pct as roce,
               net_profit_margin_pct as npm, debt_to_equity as de, free_cash_flow_cr as fcf,
               revenue_cagr_5yr, pat_cagr_5yr, composite_quality_score as composite
        FROM financial_ratios
        WHERE year = (SELECT MAX(year) FROM financial_ratios)
    """
    ratios_all = [dict(r) for r in conn.execute(metrics_query).fetchall()]
    conn.close()

    ticker_data = next((r for r in ratios_all if r["company_id"] == ticker), None)

    metrics_list = [
        "roe",
        "roce",
        "npm",
        "de",
        "fcf",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "composite",
    ]
    peer_averages = {}
    for m in metrics_list:
        vals = [r[m] for r in ratios_all if r.get(m) is not None]
        peer_averages[m] = round(sum(vals) / len(vals), 2) if vals else None

    return {
        "company_id": ticker,
        "peer_group_name": group_name,
        "is_benchmark": bool(pg_row["is_benchmark"]),
        "company_metrics": ticker_data,
        "peer_group_average": peer_averages,
    }
