import sys
from pathlib import Path
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_companies, get_ratios, get_sectors

st.set_page_config(
    page_title="Home — Nifty 100 Analytics", page_icon="📊", layout="wide"
)

st.title("📊 Nifty 100 Financial Analytics Overview")

# Sidebar Year Selector
st.sidebar.header("Filter Options")
years = [2024, 2023, 2022, 2021, 2020, 2019]
selected_year = st.sidebar.selectbox("Select Financial Year", years, index=0)

# Fetch Data
ratios_df = get_ratios(year=selected_year)
companies_df = get_companies()
sectors_df = get_sectors()

if ratios_df.empty:
    st.warning(f"No financial data available for year {selected_year}.")
else:
    # Compute 6 KPI metrics
    avg_roe = ratios_df["return_on_equity_pct"].mean()
    median_pe = ratios_df["pe_ratio"].median()
    median_de = ratios_df["debt_to_equity"].median()
    total_companies = len(companies_df)
    median_rev_cagr = ratios_df["revenue_cagr_5yr"].median()
    debt_free_count = (ratios_df["debt_to_equity"] == 0).sum()

    # 6 KPI Tiles
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Average ROE", f"{avg_roe:.2f}%" if avg_roe is not None else "N/A")
    col2.metric("Median P/E", f"{median_pe:.2f}" if median_pe else "N/A")
    col3.metric("Median D/E", f"{median_de:.2f}" if median_de else "N/A")
    col4.metric("Total Companies", total_companies)
    col5.metric(
        "Median Rev CAGR 5yr",
        f"{median_rev_cagr:.2f}%" if median_rev_cagr else "N/A",
    )
    col6.metric("Debt-Free Count", f"{debt_free_count}")

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🌐 Sector Breakdown (11 Sectors)")
        sector_summary = (
            companies_df.groupby("broad_sector")["id"]
            .count()
            .reset_index(name="company_count")
        )
        fig_donut = px.pie(
            sector_summary,
            names="broad_sector",
            values="company_count",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title=f"Sector Distribution (Nifty 100 — {total_companies} Companies)",
        )
        fig_donut.update_traces(textposition="inside", textinfo="percent+label")
        fig_donut.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=420)
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        st.subheader(f"🏆 Top 5 Companies by Composite Quality Score ({selected_year})")
        if "composite_quality_score" in ratios_df.columns:
            top5 = (
                ratios_df.sort_values(by="composite_quality_score", ascending=False)
                .head(5)[
                    [
                        "company_id",
                        "company_name",
                        "broad_sector",
                        "composite_quality_score",
                        "return_on_equity_pct",
                        "debt_to_equity",
                    ]
                ]
                .copy()
            )

            top5.columns = [
                "Ticker",
                "Company",
                "Sector",
                "Quality Score",
                "ROE (%)",
                "D/E",
            ]
            top5["Quality Score"] = top5["Quality Score"].round(2)
            top5["ROE (%)"] = top5["ROE (%)"].round(2)
            top5["D/E"] = top5["D/E"].round(2)

            st.dataframe(top5, use_container_width=True, hide_index=True)
        else:
            st.info("Composite score not computed for this selection.")
