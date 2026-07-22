import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_pl, get_ratios, get_sectors

st.set_page_config(
    page_title="Sector Analytics — Nifty 100", page_icon="🌐", layout="wide"
)

st.title("🌐 Sector Performance & Bubble Map")

sectors_df = get_sectors()

if sectors_df.empty:
    st.error("No sector data found.")
else:
    broad_sectors = sorted(sectors_df["broad_sector"].unique())
    selected_sector = st.selectbox("Select Sector", options=broad_sectors)

    # Fetch latest year ratios for sector companies
    ratios_df = get_ratios(year=2024)
    sector_ratios = ratios_df[ratios_df["broad_sector"] == selected_sector]

    if sector_ratios.empty:
        st.warning(f"No company data available for sector '{selected_sector}'.")
    else:
        # Get sales/revenue for bubble chart X axis
        pl_data = []
        for t in sector_ratios["company_id"].unique():
            pl = get_pl(t)
            if not pl.empty and "sales" in pl.columns:
                latest_pl = pl.iloc[-1]
                pl_data.append({"company_id": t, "sales": latest_pl.get("sales", 0)})

        pl_df = pd.DataFrame(pl_data)
        merged_sector = sector_ratios.merge(pl_df, on="company_id", how="left")
        merged_sector["sales"] = merged_sector["sales"].fillna(0)
        merged_sector["market_cap_crore"] = merged_sector["market_cap_crore"].fillna(
            1000
        )

        st.subheader(f"🎈 {selected_sector} — Revenue vs ROE vs Market Cap")

        fig_bubble = px.scatter(
            merged_sector,
            x="sales",
            y="return_on_equity_pct",
            size="market_cap_crore",
            color="sub_sector",
            hover_name="company_name",
            text="company_id",
            size_max=60,
            title=f"{selected_sector}: Bubble Size = Market Cap (Cr), X = Revenue, Y = ROE (%)",
            labels={
                "sales": "Revenue / Sales (₹ Cr)",
                "return_on_equity_pct": "ROE (%)",
                "market_cap_crore": "Market Cap (Cr)",
            },
        )
        fig_bubble.update_traces(textposition="top center")
        fig_bubble.update_layout(height=500, margin=dict(t=50, b=40, l=40, r=40))
        st.plotly_chart(fig_bubble, use_container_width=True)

        st.markdown("---")

        # Sector Median KPIs Bar Chart
        st.subheader(f"📊 {selected_sector} — Sector Median Key Ratios")

        kpi_cols = {
            "return_on_equity_pct": "Median ROE (%)",
            "return_on_capital_employed_pct": "Median ROCE (%)",
            "net_profit_margin_pct": "Median NPM (%)",
            "operating_profit_margin_pct": "Median OPM (%)",
            "debt_to_equity": "Median D/E",
            "pe_ratio": "Median P/E",
        }

        medians = {name: sector_ratios[col].median() for col, name in kpi_cols.items()}
        median_df = pd.DataFrame(list(medians.items()), columns=["Metric", "Value"])

        fig_bar = px.bar(
            median_df,
            x="Metric",
            y="Value",
            color="Metric",
            text_auto=".2f",
            title=f"Median Ratios across {len(sector_ratios)} Companies in {selected_sector}",
        )
        fig_bar.update_layout(
            showlegend=False, height=380, margin=dict(t=40, b=30, l=30, r=30)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
