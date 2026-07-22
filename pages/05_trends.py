import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_companies, get_ratios

st.set_page_config(
    page_title="Financial Trends — Nifty 100", page_icon="📉", layout="wide"
)

st.title("📉 10-Year Financial Trends & YoY Overlay")

companies_df = get_companies()
options = [f"{r['company_name']} ({r['id']})" for _, r in companies_df.iterrows()]
company_map = {
    f"{r['company_name']} ({r['id']})": r["id"] for _, r in companies_df.iterrows()
}

selected_company = st.selectbox("Select Company", options=options, index=0)
ticker = company_map[selected_company]

# Ratio metrics available for trend line overlay
metric_options = {
    "return_on_equity_pct": "Return on Equity (%)",
    "operating_profit_margin_pct": "Operating Profit Margin (%)",
    "net_profit_margin_pct": "Net Profit Margin (%)",
    "debt_to_equity": "Debt to Equity",
    "free_cash_flow_cr": "Free Cash Flow (₹ Cr)",
    "interest_coverage": "Interest Coverage Ratio",
    "asset_turnover": "Asset Turnover",
}

selected_metrics = st.multiselect(
    "Select up to 3 Metrics to Overlay",
    options=list(metric_options.keys()),
    default=["return_on_equity_pct", "operating_profit_margin_pct"],
    format_func=lambda x: metric_options[x],
    max_selections=3,
)

ratios_df = get_ratios(ticker=ticker)

if ratios_df.empty or not selected_metrics:
    st.info("Please select at least one metric to visualize.")
else:
    fig = go.Figure()

    for m in selected_metrics:
        sub_df = ratios_df[["year", m]].dropna().sort_values(by="year")
        if not sub_df.empty:
            # Compute YoY % change annotations
            sub_df["yoy_pct"] = sub_df[m].pct_change() * 100

            text_labels = []
            for idx, row in sub_df.iterrows():
                val = row[m]
                yoy = row["yoy_pct"]
                if pd.notnull(yoy):
                    sign = "+" if yoy >= 0 else ""
                    text_labels.append(f"{val:.1f}<br>({sign}{yoy:.1f}%)")
                else:
                    text_labels.append(f"{val:.1f}")

            fig.add_trace(
                go.Scatter(
                    x=sub_df["year"],
                    y=sub_df[m],
                    name=metric_options[m],
                    mode="lines+markers+text",
                    text=text_labels,
                    textposition="top center",
                    line=dict(width=3),
                )
            )

    fig.update_layout(
        title=f"10-Year Multi-Metric Trend for {selected_company} (with YoY Annotations)",
        xaxis_title="Financial Year",
        yaxis_title="Metric Value",
        height=500,
        margin=dict(t=50, b=40, l=40, r=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📄 Raw Financial Ratios Table")
    st.dataframe(
        ratios_df.sort_values(by="year", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
