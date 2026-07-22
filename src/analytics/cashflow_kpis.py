"""src/analytics/cashflow_kpis.py

==============================
Sprint 2 & Sprint 5 — Cash-flow derived KPIs, Capital Allocation Classifier,
and Cash Flow Intelligence Reports.
"""

from __future__ import annotations

import csv
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Capital-allocation pattern labels
PATTERN_REINVESTOR = "Reinvestor"
PATTERN_SHAREHOLDER_RETURNS = "Shareholder Returns"
PATTERN_LIQUIDATING_ASSETS = "Liquidating Assets"
PATTERN_DISTRESS_SIGNAL = "Distress Signal"
PATTERN_GROWTH_BY_DEBT = "Growth Funded by Debt"
PATTERN_CASH_ACCUMULATOR = "Cash Accumulator"
PATTERN_PRE_REVENUE = "Pre-Revenue"
PATTERN_MIXED = "Mixed"

_ALLOCATION_MAP: dict[tuple, str] = {
    (+1, -1, -1): PATTERN_REINVESTOR,
    (+1, -1, +1): PATTERN_GROWTH_BY_DEBT,
    (+1, +1, -1): PATTERN_SHAREHOLDER_RETURNS,
    (+1, +1, +1): PATTERN_CASH_ACCUMULATOR,
    (-1, +1, +1): PATTERN_LIQUIDATING_ASSETS,
    (-1, -1, +1): PATTERN_PRE_REVENUE,
    (-1, +1, -1): PATTERN_DISTRESS_SIGNAL,
    (-1, -1, -1): PATTERN_MIXED,
}


def _sign(value: Optional[float]) -> int:
    """Return +1 for positive, -1 for non-positive (treats 0 as negative)."""
    if value is None or value <= 0:
        return -1
    return +1


def free_cash_flow(
    operating_activity: Optional[float],
    investing_activity: Optional[float],
) -> Optional[float]:
    """Free Cash Flow (Cr) = Cash from Operations + Cash from Investing."""
    if operating_activity is None and investing_activity is None:
        return None
    cfo = operating_activity or 0.0
    cfi = investing_activity or 0.0
    return round(cfo + cfi, 4)


def cfo_quality_score(
    cfo_list: List[Optional[float]],
    pat_list: List[Optional[float]],
) -> str:
    """CFO Quality Score — measures earnings quality via cash conversion.

    Thresholds:
    avg >= 0.75  → "High Quality"
    avg >= 0.40  → "Moderate"
    else        → "Accrual Risk"
    """
    ratios = []
    for cfo, pat in zip(cfo_list, pat_list):
        if cfo is not None and pat is not None and pat != 0:
            ratios.append(cfo / pat)

    if len(ratios) < 2:
        return "Insufficient Data"

    avg = sum(ratios) / len(ratios)
    if avg >= 0.75:
        return "High Quality"
    if avg >= 0.40:
        return "Moderate"
    return "Accrual Risk"


def capex_intensity(
    investing_activity: Optional[float],
    sales: Optional[float],
) -> Optional[str]:
    """CapEx Intensity Label.

    Proxy: |investing_activity| / sales
    < 0.05 (5%)  → "Asset Light"
    < 0.15 (15%) → "Moderate"
    >= 0.15      → "Capital Intensive"
    """
    if sales is None or sales == 0 or investing_activity is None:
        return None
    intensity = abs(investing_activity) / abs(sales)
    if intensity < 0.05:
        return "Asset Light"
    if intensity < 0.15:
        return "Moderate"
    return "Capital Intensive"


def fcf_conversion_rate(
    fcf: Optional[float],
    operating_profit: Optional[float],
) -> Optional[float]:
    """FCF Conversion Rate = Free Cash Flow / Operating Profit."""
    if fcf is None or operating_profit is None:
        return None
    if operating_profit == 0:
        return None
    return round(fcf / operating_profit, 4)


def classify_capital_allocation(
    cfo: Optional[float],
    cfi: Optional[float],
    cff: Optional[float],
) -> str:
    """Classify capital allocation pattern based on signs of CFO, CFI, CFF."""
    key = (_sign(cfo), _sign(cfi), _sign(cff))
    return _ALLOCATION_MAP.get(key, PATTERN_MIXED)


def generate_capital_allocation_csv(
    db_path: Path = DB_PATH,
    output_path: Path = OUTPUT_DIR / "capital_allocation.csv",
) -> int:
    """Read all cashflow rows and write capital-allocation pattern to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT company_id, year,
                   operating_activity, investing_activity, financing_activity
            FROM   cashflow
            ORDER  BY company_id, year
            """
        ).fetchall()

    written = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company_id",
                "year",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label",
            ],
        )
        writer.writeheader()

        for row in rows:
            cfo = row["operating_activity"]
            cfi = row["investing_activity"]
            cff = row["financing_activity"]
            pattern = classify_capital_allocation(cfo, cfi, cff)

            writer.writerow(
                {
                    "company_id": row["company_id"],
                    "year": int(row["year"]),
                    "cfo_sign": _sign(cfo),
                    "cfi_sign": _sign(cfi),
                    "cff_sign": _sign(cff),
                    "pattern_label": pattern,
                }
            )
            written += 1

    logger.info("Capital allocation CSV written → %s  (%d rows)", output_path, written)
    return written


def generate_cashflow_intelligence():
    """Generates Days 31 & 32 reports:

    - output/cashflow_intelligence.xlsx
    - output/distress_alerts.csv
    - output/pattern_changes.csv
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))

    # Fetch companies and sectors
    companies = pd.read_sql_query(
        "SELECT c.id, c.company_name, s.broad_sector as sector FROM companies c LEFT JOIN sectors s ON c.id = s.company_id",
        conn,
    )

    # Fetch cashflow, P&L, balance sheet, and ratio data
    cf_df = pd.read_sql_query(
        "SELECT * FROM cashflow ORDER BY company_id, year ASC", conn
    )
    pl_df = pd.read_sql_query(
        "SELECT * FROM profitandloss ORDER BY company_id, year ASC", conn
    )
    bs_df = pd.read_sql_query(
        "SELECT * FROM balancesheet ORDER BY company_id, year ASC", conn
    )
    ratios_df = pd.read_sql_query(
        "SELECT * FROM financial_ratios ORDER BY company_id, year ASC", conn
    )

    conn.close()

    # Generate capital_allocation.csv first
    generate_capital_allocation_csv(DB_PATH, OUTPUT_DIR / "capital_allocation.csv")

    intel_rows = []
    distress_rows = []

    for _, comp in companies.iterrows():
        cid = comp["id"]
        sec = comp["sector"] or "Unassigned"

        c_cf = cf_df[cf_df["company_id"] == cid]
        c_pl = pl_df[pl_df["company_id"] == cid]
        c_bs = bs_df[bs_df["company_id"] == cid]
        c_ratios = ratios_df[ratios_df["company_id"] == cid]

        if c_cf.empty or c_pl.empty:
            continue

        latest_cf = c_cf.iloc[-1]
        latest_pl = c_pl.iloc[-1]
        latest_bs = c_bs.iloc[-1] if not c_bs.empty else None
        latest_ratio = c_ratios.iloc[-1] if not c_ratios.empty else None

        # 1. CFO Quality Score (5-year average CFO/PAT)
        cfo_list = c_cf["operating_activity"].tail(5).tolist()
        pat_list = c_pl["net_profit"].tail(5).tolist()
        cfo_label = cfo_quality_score(cfo_list, pat_list)

        valid_ratios = [
            c / p
            for c, p in zip(cfo_list, pat_list)
            if c is not None and p is not None and p != 0
        ]
        avg_cfo_pat = sum(valid_ratios) / len(valid_ratios) if valid_ratios else None

        # 2. CapEx Intensity
        cfi_val = latest_cf.get("investing_activity")
        sales_val = latest_pl.get("sales")
        capex_lbl = capex_intensity(cfi_val, sales_val) or "N/A"
        capex_pct = (
            (abs(cfi_val) / abs(sales_val)) * 100
            if sales_val and sales_val != 0 and cfi_val is not None
            else None
        )

        # 3. Distress Signal: CFO < 0 AND CFF > 0 (latest year)
        cfo_latest = latest_cf.get("operating_activity", 0) or 0
        cff_latest = latest_cf.get("financing_activity", 0) or 0
        distress_flag = bool(cfo_latest < 0 and cff_latest > 0)

        if distress_flag:
            distress_rows.append(
                {
                    "company_id": cid,
                    "company_name": comp["company_name"],
                    "sector": sec,
                    "cfo_value": cfo_latest,
                    "cff_value": cff_latest,
                    "latest_net_profit": latest_pl.get("net_profit", 0),
                }
            )

        # 4. Deleveraging Flag: CFF < 0 AND borrowings declining YoY
        deleveraging_flag = False
        if latest_bs is not None and len(c_bs) >= 2:
            b_curr = c_bs.iloc[-1].get("borrowings", 0) or 0
            b_prev = c_bs.iloc[-2].get("borrowings", 0) or 0
            if cff_latest < 0 and b_curr < b_prev:
                deleveraging_flag = True

        # 5. FCF CAGR 5yr and FCF Conversion %
        fcf_hist = c_ratios["free_cash_flow_cr"].dropna()
        if len(fcf_hist) >= 5 and fcf_hist.iloc[-5] > 0 and fcf_hist.iloc[-1] > 0:
            fcf_cagr = ((fcf_hist.iloc[-1] / fcf_hist.iloc[-5]) ** (1 / 4) - 1) * 100
        else:
            fcf_cagr = None

        fcf_conv = (
            latest_ratio.get("fcf_conversion_rate")
            if latest_ratio is not None
            else None
        )
        fcf_conv_pct = fcf_conv * 100 if fcf_conv is not None else None

        # 6. Capital Allocation Pattern Label
        cap_alloc_lbl = classify_capital_allocation(cfo_latest, cfi_val, cff_latest)

        intel_rows.append(
            {
                "company_id": cid,
                "sector": sec,
                "cfo_quality_score": (
                    round(avg_cfo_pat, 2) if avg_cfo_pat is not None else None
                ),
                "cfo_quality_label": cfo_label,
                "capex_intensity_pct": (
                    round(capex_pct, 2) if capex_pct is not None else None
                ),
                "capex_label": capex_lbl,
                "fcf_cagr_5yr": round(fcf_cagr, 2) if fcf_cagr else None,
                "fcf_conversion_pct": round(fcf_conv_pct, 2) if fcf_conv_pct else None,
                "distress_flag": "YES" if distress_flag else "NO",
                "deleveraging_flag": "YES" if deleveraging_flag else "NO",
                "capital_allocation_label": cap_alloc_lbl,
            }
        )

    intel_df = pd.DataFrame(intel_rows)

    # Export output/cashflow_intelligence.xlsx
    excel_path = OUTPUT_DIR / "cashflow_intelligence.xlsx"
    intel_df.to_excel(excel_path, index=False)
    print(f"✅ Exported {len(intel_df)} rows to {excel_path.name}")

    # Export output/distress_alerts.csv
    distress_df = pd.DataFrame(distress_rows)
    distress_csv = OUTPUT_DIR / "distress_alerts.csv"
    distress_df.to_csv(distress_csv, index=False)
    print(f"✅ Exported {len(distress_df)} distress alerts to {distress_csv.name}")

    # Day 32 — Generate output/pattern_changes.csv (YoY pattern shifts)
    cap_csv_path = OUTPUT_DIR / "capital_allocation.csv"
    if cap_csv_path.exists():
        cap_df = pd.read_csv(cap_csv_path)
        pattern_changes = []
        for cid, group in cap_df.groupby("company_id"):
            group = group.sort_values(by="year")
            if len(group) >= 2:
                for i in range(1, len(group)):
                    prev_p = group.iloc[i - 1]["pattern_label"]
                    curr_p = group.iloc[i]["pattern_label"]
                    yr = group.iloc[i]["year"]
                    if prev_p != curr_p:
                        pattern_changes.append(
                            {
                                "company_id": cid,
                                "year": yr,
                                "previous_pattern": prev_p,
                                "new_pattern": curr_p,
                            }
                        )

        changes_df = pd.DataFrame(pattern_changes)
        changes_csv = OUTPUT_DIR / "pattern_changes.csv"
        changes_df.to_csv(changes_csv, index=False)
        print(f"✅ Exported {len(changes_df)} YoY pattern shifts to {changes_csv.name}")

    return intel_df, distress_df


if __name__ == "__main__":
    generate_cashflow_intelligence()
