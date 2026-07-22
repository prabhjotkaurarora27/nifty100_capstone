"""
src/screener/radar_chart.py
============================
Sprint 3 — Day 19
Generate per-company radar (polar) charts with 8 axes.

Axes: ROE, ROCE, NPM, D/E (score), FCF (score), PAT CAGR 5yr,
      Revenue CAGR 5yr, Composite Score

Each chart shows:
  - Company values as filled polygon
  - Peer group average as dashed outline overlay
  - Companies with no peer group: Nifty 100 average as reference

Output: reports/radar_charts/{company_id}_radar.png

Run with:
    python -m src.screener.radar_chart
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "reports" / "radar_charts"

# ── 8 radar axes: (display_label, column_in_financial_ratios, invert_for_de) ──
RADAR_AXES: List[tuple] = [
    ("ROE", "return_on_equity_pct", False),
    ("ROCE", "return_on_capital_employed_pct", False),
    ("NPM", "net_profit_margin_pct", False),
    ("D/E Score", "debt_to_equity", True),  # inverted
    ("FCF Score", "free_cash_flow_cr", False),
    ("PAT CAGR 5yr", "pat_cagr_5yr", False),
    ("Rev CAGR 5yr", "revenue_cagr_5yr", False),
    ("Quality Score", "composite_quality_score", False),
]

N_AXES = len(RADAR_AXES)
ANGLES = np.linspace(0, 2 * np.pi, N_AXES, endpoint=False).tolist()
ANGLES += ANGLES[:1]  # close the polygon

# Winsorisation limits per metric for normalising to 0–100
WINSOR_PARAMS: Dict[str, tuple] = {
    "return_on_equity_pct": (0, 60),
    "return_on_capital_employed_pct": (0, 50),
    "net_profit_margin_pct": (-5, 40),
    "debt_to_equity": (0, 5),  # inverted: 0 DE → 100 score
    "free_cash_flow_cr": (-5000, 20000),
    "pat_cagr_5yr": (-20, 50),
    "revenue_cagr_5yr": (-10, 40),
    "composite_quality_score": (0, 100),
}


def _scale(value: Optional[float], col: str, invert: bool) -> float:
    """Scale a raw metric value to 0–100 using predefined winsorisation bounds."""
    lo, hi = WINSOR_PARAMS.get(col, (0, 100))
    if value is None or pd.isna(value):
        return 0.0
    v = max(lo, min(hi, float(value)))
    if hi == lo:
        return 50.0
    scaled = (v - lo) / (hi - lo) * 100.0
    return (100.0 - scaled) if invert else scaled


def _values_for_row(row: pd.Series) -> List[float]:
    """Extract and scale 8 axis values from a DataFrame row."""
    return [_scale(row.get(col), col, inv) for _, col, inv in RADAR_AXES]


def _make_radar_chart(
    company_id: str,
    company_name: str,
    company_vals: List[float],
    reference_vals: List[float],
    reference_label: str,
    output_path: Path,
) -> None:
    """Render and save a polar radar chart PNG."""
    # Close polygon
    comp_plot = company_vals + company_vals[:1]
    ref_plot = reference_vals + reference_vals[:1]
    labels = [ax[0] for ax in RADAR_AXES]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Grid lines
    ax.set_rgrids(
        [20, 40, 60, 80, 100],
        labels=["20", "40", "60", "80", "100"],
        angle=22.5,
        fontsize=7,
        color="grey",
    )
    ax.set_ylim(0, 100)

    # Axis labels
    ax.set_thetagrids(
        np.degrees(ANGLES[:-1]),
        labels=labels,
        fontsize=11,
        fontweight="bold",
    )

    # Reference overlay (dashed)
    ax.plot(
        ANGLES,
        ref_plot,
        linestyle="--",
        linewidth=1.5,
        color="#FF6B35",
        alpha=0.85,
        label=reference_label,
    )
    ax.fill(ANGLES, ref_plot, color="#FF6B35", alpha=0.08)

    # Company polygon (filled)
    ax.plot(
        ANGLES, comp_plot, linewidth=2.0, color="#1B4F8A", alpha=0.9, label=company_id
    )
    ax.fill(ANGLES, comp_plot, color="#1B4F8A", alpha=0.20)

    # Title
    ax.set_title(
        f"{company_name}\n({company_id})",
        pad=18,
        fontsize=13,
        fontweight="bold",
        color="#1B4F8A",
    )

    # Legend
    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.30, 1.10),
        fontsize=10,
        framealpha=0.7,
    )

    # Subtle background
    ax.set_facecolor("#F8F9FA")
    fig.patch.set_facecolor("#FFFFFF")

    plt.tight_layout()
    plt.savefig(
        output_path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor()
    )
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# Data loaders
# ─────────────────────────────────────────────────────────────────────────────


def _load_company_data(db_path: Path) -> pd.DataFrame:
    """Latest-year financials + composite score for all companies."""
    metric_cols = ", ".join(f"fr.{col}" for _, col, _ in RADAR_AXES)
    sql = f"""
    SELECT fr.company_id, c.company_name,
           {metric_cols}
    FROM financial_ratios fr
    JOIN companies c ON fr.company_id = c.id
    WHERE fr.year = (
        SELECT MAX(year) FROM financial_ratios fr2
        WHERE fr2.company_id = fr.company_id
          AND fr2.return_on_equity_pct IS NOT NULL
    )
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(sql, conn)
    return df.set_index("company_id")


def _load_peer_group_map(db_path: Path) -> Dict[str, str]:
    """Return {company_id: peer_group_name}."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT company_id, peer_group_name FROM peer_groups"
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def _group_averages(
    df: pd.DataFrame, peer_map: Dict[str, str]
) -> Dict[str, List[float]]:
    """Compute scaled average values per peer group and for Nifty 100."""
    # Nifty 100 average (all companies)
    nifty_avg = [
        np.nanmean(
            [
                _scale(df.loc[cid, col] if cid in df.index else None, col, inv)
                for cid in df.index
            ]
        )
        for _, col, inv in RADAR_AXES
    ]

    group_avgs: Dict[str, List[float]] = {"Nifty 100": nifty_avg}

    # Per peer group
    from collections import defaultdict

    group_companies: Dict[str, List[str]] = defaultdict(list)
    for cid, grp in peer_map.items():
        group_companies[grp].append(cid)

    for grp, members in group_companies.items():
        avgs = []
        for _, col, inv in RADAR_AXES:
            vals = [
                _scale(df.loc[cid, col] if cid in df.index else None, col, inv)
                for cid in members
            ]
            avgs.append(float(np.nanmean(vals)) if vals else 0.0)
        group_avgs[grp] = avgs

    return group_avgs


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def generate_radar_chart(
    company_id: str,
    company_row: pd.Series,
    company_name: str,
    reference_vals: List[float],
    reference_label: str,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Generate and save a radar chart for one company."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{company_id}_radar.png"
    company_vals = _values_for_row(company_row)
    _make_radar_chart(
        company_id,
        company_name,
        company_vals,
        reference_vals,
        reference_label,
        output_path,
    )
    return output_path


def generate_all_radar_charts(
    db_path: Path = config.DB_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> int:
    """
    Generate radar PNGs for all 92 companies.

    Companies in a peer group: use peer group average as reference.
    Companies with no peer group: use Nifty 100 average as reference.

    Returns
    -------
    int : number of charts generated
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _load_company_data(db_path)
    peer_map = _load_peer_group_map(db_path)
    avgs = _group_averages(df, peer_map)

    count = 0
    for company_id, row in df.iterrows():
        company_name = row.get("company_name", company_id)
        peer_group = peer_map.get(company_id)

        if peer_group and peer_group in avgs:
            ref_vals = avgs[peer_group]
            ref_label = f"{peer_group} Avg"
        else:
            ref_vals = avgs["Nifty 100"]
            ref_label = "Nifty 100 Avg"

        out_path = generate_radar_chart(
            company_id,
            row,
            company_name,
            ref_vals,
            ref_label,
            output_dir,
        )
        count += 1
        if count % 20 == 0:
            logger.info("  Radar charts generated: %d", count)

    logger.info("✓ All %d radar charts written → %s", count, output_dir)
    return count


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    n = generate_all_radar_charts()
    print(f"\n✓ Generated {n} radar charts → {OUTPUT_DIR}")
