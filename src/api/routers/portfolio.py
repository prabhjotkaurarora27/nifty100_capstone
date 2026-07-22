from pathlib import Path
from fastapi import APIRouter, HTTPException
import pandas as pd

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_STATS_CSV = PROJECT_ROOT / "output" / "portfolio_stats.csv"


@router.get("/stats")
def get_portfolio_stats():
    """Fetch portfolio P10–P90 percentile statistics across 10 core financial KPIs."""
    if not PORTFOLIO_STATS_CSV.exists():
        # Fallback if file not yet generated
        from src.analytics.clustering import run_clustering_and_analytics

        run_clustering_and_analytics()

    if not PORTFOLIO_STATS_CSV.exists():
        raise HTTPException(
            status_code=500, detail="Portfolio statistics report unavailable."
        )

    df = pd.read_csv(PORTFOLIO_STATS_CSV)
    return {"count": len(df), "stats": df.to_dict(orient="records")}
