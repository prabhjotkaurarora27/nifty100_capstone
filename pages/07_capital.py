import sys
from pathlib import Path
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_ratios

st.set_page_config(
    page_title="Capital Allocation — Nifty 100", page_icon="🧱", layout="wide"
)

st.title("🧱 Capital Allocation Pattern Treemap")

ratios_df = get_ratios(year=2024)

if ratios_df.empty or "capital_allocation_pattern" not in ratios_df.columns:
    st.error("Capital allocation pattern data is unavailable.")
else:
    df_tree = ratios_df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "capital_allocation_pattern",
            "market_cap_crore",
            "free_cash_flow_cr",
            "return_on_equity_pct",
        ]
    ].copy()

    df_tree["capital_allocation_pattern"] = df_tree[
        "capital_allocation_pattern"
    ].fillna("Unclassified / Balanced")
    df_tree["market_cap_crore"] = df_tree["market_cap_crore"].fillna(1000)

    # Plotly Treemap
    st.subheader(
        "🗺️ Nifty 100 Companies Grouped by Capital Allocation Patterns"
    )

    fig_tree = px.treemap(
        df_tree,
        path=["capital_allocation_pattern", "broad_sector", "company_id"],
        values="market_cap_crore",
        color="return_on_equity_pct",
        color_continuous_scale="Viridis",
        hover_data=["company_name", "free_cash_flow_cr", "return_on_equity_pct"],
        title="Treemap: Capital Allocation Archetypes → Sector → Company (Sized by MCap, Coloured by ROE)",
    )
    fig_tree.update_layout(height=600, margin=dict(t=50, b=30, l=30, r=30))
    st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("---")

    # Interactive Pattern Filter
    patterns = sorted(df_tree["capital_allocation_pattern"].unique())
    st.subheader("🔍 Filter Companies by Capital Allocation Pattern")
    selected_pattern = st.selectbox("Select Archetype Pattern", options=patterns)

    matching_df = df_tree[
        df_tree["capital_allocation_pattern"] == selected_pattern
    ][
        [
            "company_id",
            "company_name",
            "broad_sector",
            "return_on_equity_pct",
            "free_cash_flow_cr",
            "market_cap_crore",
        ]
    ].copy()

    matching_df.columns = [
        "Ticker",
        "Company Name",
        "Sector",
        "ROE (%)",
        "FCF (Cr)",
        "Market Cap (Cr)",
    ]

    st.markdown(
        f"### `{len(matching_df)} companies categorized as '{selected_pattern}'`"
    )
    st.dataframe(matching_df, use_container_width=True, hide_index=True)
