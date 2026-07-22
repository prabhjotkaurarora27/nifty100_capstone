import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import (
    get_companies,
    get_pl,
    get_pros_cons,
    get_ratios,
)

st.set_page_config(
    page_title="Company Profile — Nifty 100", page_icon="🏢", layout="wide"
)

st.title("🏢 Company Profile & Financial Deep-Dive")

# Load companies for autocomplete dropdown
companies_df = get_companies()
options = []
company_lookup = {}

for _, row in companies_df.iterrows():
    label = f"{row['company_name']} ({row['id']})"
    options.append(label)
    company_lookup[label] = row["id"]
    company_lookup[row["id"]] = row["id"]
    company_lookup[row["company_name"]] = row["id"]

selected_option = st.selectbox(
    "Search Company (by Name or Ticker)",
    options=options,
    index=0 if options else None,
)

ticker = company_lookup.get(selected_option) if selected_option else "RELIANCE"

if not ticker or ticker not in companies_df["id"].values:
    st.error("Ticker not found — please try another")
else:
    company_info = companies_df[companies_df["id"] == ticker].iloc[0]
    ratios_df = get_ratios(ticker=ticker)
    pl_df = get_pl(ticker)
    pc_df = get_pros_cons(ticker)

    # Company Card Header
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"{company_info['company_name']} ({company_info['id']})")
        st.write(
            f"**Sector**: {company_info.get('broad_sector', 'N/A')} | **Sub-Sector**: {company_info.get('sub_sector', 'N/A')}"
        )
        st.write(f"_{company_info.get('about_company', 'No description available.')}_")
    with c2:
        if company_info.get("website") and str(company_info.get("website")) != "nan":
            st.markdown(f"[🌐 Official Website]({company_info['website']})")

    st.markdown("---")

    # 6 KPI Tiles (Latest year)
    if not ratios_df.empty:
        latest = ratios_df.iloc[-1]
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        roe = latest.get("return_on_equity_pct")
        roce = latest.get("return_on_capital_employed_pct")
        npm = latest.get("net_profit_margin_pct")
        de = latest.get("debt_to_equity")
        cagr5 = latest.get("revenue_cagr_5yr")
        fcf = latest.get("free_cash_flow_cr")

        col1.metric("ROE", f"{roe:.2f}%" if pd.notnull(roe) else "N/A")
        col2.metric("ROCE", f"{roce:.2f}%" if pd.notnull(roce) else "N/A")
        col3.metric("Net Profit Margin", f"{npm:.2f}%" if pd.notnull(npm) else "N/A")
        col4.metric("D/E", f"{de:.2f}" if pd.notnull(de) else "N/A")
        col5.metric("Rev CAGR 5yr", f"{cagr5:.2f}%" if pd.notnull(cagr5) else "N/A")
        col6.metric("FCF (Latest Cr)", f"₹{fcf:,.1f}" if pd.notnull(fcf) else "N/A")

    st.markdown("---")

    # Charts Layout
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📊 10-Year Revenue & Net Profit Trend (₹ Cr)")
        if not pl_df.empty and "sales" in pl_df.columns:
            fig_bar = go.Figure()
            fig_bar.add_trace(
                go.Bar(
                    x=pl_df["year"],
                    y=pl_df["sales"],
                    name="Revenue (Sales)",
                    marker_color="#2b5c8f",
                )
            )
            fig_bar.add_trace(
                go.Bar(
                    x=pl_df["year"],
                    y=pl_df["net_profit"],
                    name="Net Profit",
                    marker_color="#36b37e",
                )
            )
            fig_bar.update_layout(
                barmode="group",
                xaxis_title="Year",
                yaxis_title="Amount (₹ Crore)",
                height=400,
                margin=dict(t=30, b=30, l=30, r=30),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No P&L trend data available.")

    with col_chart2:
        st.subheader("📈 10-Year ROE & ROCE Return Rates (%)")
        if not ratios_df.empty:
            fig_dual = make_subplots(specs=[[{"secondary_y": False}]])
            fig_dual.add_trace(
                go.Scatter(
                    x=ratios_df["year"],
                    y=ratios_df["return_on_equity_pct"],
                    name="ROE (%)",
                    mode="lines+markers",
                    line=dict(color="#ff9900", width=3),
                )
            )
            fig_dual.add_trace(
                go.Scatter(
                    x=ratios_df["year"],
                    y=ratios_df["return_on_capital_employed_pct"],
                    name="ROCE (%)",
                    mode="lines+markers",
                    line=dict(color="#00b8d9", width=3),
                )
            )
            fig_dual.update_layout(
                xaxis_title="Year",
                yaxis_title="Percentage (%)",
                height=400,
                margin=dict(t=30, b=30, l=30, r=30),
            )
            st.plotly_chart(fig_dual, use_container_width=True)
        else:
            st.info("No return ratio trends available.")

    st.markdown("---")

    # Pros and Cons Badges
    st.subheader("⚖️ Investment Pros & Cons")
    if not pc_df.empty:
        pros_text = pc_df.iloc[0].get("pros", "")
        cons_text = pc_df.iloc[0].get("cons", "")

        col_p, col_c = st.columns(2)
        with col_p:
            st.markdown("##### ✅ Pros / Key Strengths")
            if pros_text and str(pros_text) != "nan":
                for item in str(pros_text).split(";"):
                    if item.strip():
                        st.success(f"✅ {item.strip()}")
            else:
                st.write("No specific pros documented.")

        with col_c:
            st.markdown("##### ❌ Cons / Key Risks")
            if cons_text and str(cons_text) != "nan":
                for item in str(cons_text).split(";"):
                    if item.strip():
                        st.error(f"❌ {item.strip()}")
            else:
                st.write("No specific cons documented.")
    else:
        st.info("Pros and cons analysis not available for this ticker.")
