import sys
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_ratios
from src.screener.engine import ScreenerEngine

st.set_page_config(
    page_title="Screener — Nifty 100 Analytics", page_icon="🔍", layout="wide"
)

st.title("🔍 Financial Screener & Quality Filter Engine")

# Initialize Screener Engine
engine = ScreenerEngine()

# Sidebar Presets & Sliders
st.sidebar.header("Filter Presets")
preset_cols = st.sidebar.columns(2)

# Session state initialization for sliders
defaults = {
    "roe_min": 0.0,
    "de_max": 10.0,
    "fcf_min": -5000.0,
    "rev_cagr_min": -50.0,
    "pat_cagr_min": -50.0,
    "opm_min": -50.0,
    "pe_max": 200.0,
    "pb_max": 50.0,
    "div_yield_min": 0.0,
    "icr_min": 0.0,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Preset Buttons
if preset_cols[0].button("Quality"):
    st.session_state["roe_min"] = 15.0
    st.session_state["de_max"] = 1.0
    st.session_state["fcf_min"] = 0.0
    st.session_state["rev_cagr_min"] = 10.0

if preset_cols[1].button("Value"):
    st.session_state["pe_max"] = 20.0
    st.session_state["pb_max"] = 3.0
    st.session_state["de_max"] = 2.0
    st.session_state["div_yield_min"] = 1.0

if preset_cols[0].button("Growth"):
    st.session_state["pat_cagr_min"] = 20.0
    st.session_state["rev_cagr_min"] = 15.0
    st.session_state["de_max"] = 2.0

if preset_cols[1].button("Dividend"):
    st.session_state["div_yield_min"] = 2.0
    st.session_state["fcf_min"] = 0.0

if preset_cols[0].button("Debt-Free"):
    st.session_state["de_max"] = 0.0
    st.session_state["roe_min"] = 12.0

if preset_cols[1].button("Reset All"):
    for k, v in defaults.items():
        st.session_state[k] = v

st.sidebar.markdown("---")
st.sidebar.header("Custom Sliders")

roe_min = st.sidebar.slider(
    "ROE Min (%)", -20.0, 100.0, float(st.session_state["roe_min"]), key="roe_s"
)
de_max = st.sidebar.slider(
    "D/E Max", 0.0, 10.0, float(st.session_state["de_max"]), key="de_s"
)
fcf_min = st.sidebar.slider(
    "FCF Min (₹ Cr)",
    -15000.0,
    20000.0,
    float(st.session_state["fcf_min"]),
    key="fcf_s",
)
rev_cagr_min = st.sidebar.slider(
    "Revenue CAGR 5yr Min (%)",
    -20.0,
    50.0,
    float(st.session_state["rev_cagr_min"]),
    key="rev_s",
)
pat_cagr_min = st.sidebar.slider(
    "PAT CAGR 5yr Min (%)",
    -20.0,
    50.0,
    float(st.session_state["pat_cagr_min"]),
    key="pat_s",
)
opm_min = st.sidebar.slider(
    "OPM Min (%)", -20.0, 80.0, float(st.session_state["opm_min"]), key="opm_s"
)
pe_max = st.sidebar.slider(
    "P/E Max", 0.0, 200.0, float(st.session_state["pe_max"]), key="pe_s"
)
pb_max = st.sidebar.slider(
    "P/B Max", 0.0, 50.0, float(st.session_state["pb_max"]), key="pb_s"
)
div_yield_min = st.sidebar.slider(
    "Dividend Yield Min (%)",
    0.0,
    10.0,
    float(st.session_state["div_yield_min"]),
    key="div_s",
)
icr_min = st.sidebar.slider(
    "ICR Min", 0.0, 50.0, float(st.session_state["icr_min"]), key="icr_s"
)

# Filtering logic
filters = {}
if roe_min > -20.0:
    filters["roe_min"] = roe_min
if de_max < 10.0:
    filters["de_max"] = de_max
if fcf_min > -15000.0:
    filters["fcf_min"] = fcf_min
if rev_cagr_min > -20.0:
    filters["revenue_cagr_5yr_min"] = rev_cagr_min
if pat_cagr_min > -20.0:
    filters["pat_cagr_5yr_min"] = pat_cagr_min
if opm_min > -20.0:
    filters["opm_min"] = opm_min
if pe_max < 200.0:
    filters["pe_max"] = pe_max
if pb_max < 50.0:
    filters["pb_max"] = pb_max
if div_yield_min > 0.0:
    filters["dividend_yield_min"] = div_yield_min
if icr_min > 0.0:
    filters["icr_min"] = icr_min

filtered_df = engine.apply_filters(filters)

# Display Results
st.subheader(f"📊 Filter Results")
st.markdown(f"### `{len(filtered_df)} companies match your filters`")

display_cols = [
    "company_id",
    "company_name",
    "broad_sector",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]

# Rename columns for presentation
rename_dict = {
    "company_id": "Ticker",
    "company_name": "Company Name",
    "broad_sector": "Sector",
    "composite_quality_score": "Composite Score",
    "return_on_equity_pct": "ROE (%)",
    "debt_to_equity": "D/E",
    "free_cash_flow_cr": "FCF (Cr)",
    "revenue_cagr_5yr": "Rev CAGR 5y (%)",
    "pat_cagr_5yr": "PAT CAGR 5y (%)",
    "operating_profit_margin_pct": "OPM (%)",
    "pe_ratio": "P/E",
    "pb_ratio": "P/B",
    "dividend_yield_pct": "Div Yield (%)",
    "interest_coverage": "ICR",
}

if not filtered_df.empty:
    present_cols = [c for c in display_cols if c in filtered_df.columns]
    res_table = filtered_df[present_cols].rename(columns=rename_dict).copy()
    st.dataframe(res_table, use_container_width=True, hide_index=True)

    # Download CSV button
    csv_data = res_table.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Results CSV",
        data=csv_data,
        file_name="nifty100_screener_results.csv",
        mime="text/csv",
    )
else:
    st.info("No companies matched the current filter threshold combination.")
