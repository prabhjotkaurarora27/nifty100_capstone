import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_peers, get_ratios

st.set_page_config(
    page_title="Peer Analytics — Nifty 100", page_icon="🥊", layout="wide"
)

st.title("🥊 Peer Group Analytics & Radar Visualizer")

# Fetch all peer group names
peers_df = get_peers()

if peers_df.empty:
    st.error("No peer group data found.")
else:
    group_names = sorted(peers_df["peer_group_name"].unique())
    selected_group = st.selectbox("Select Peer Group", options=group_names)

    # Fetch detailed metrics for selected peer group
    group_details = get_peers(group_name=selected_group)

    # Get unique member companies in group
    group_companies = group_details[
        ["company_id", "company_name", "is_benchmark"]
    ].drop_duplicates()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🎯 Select Focus Company")
        focus_ticker = st.selectbox(
            "Company to Compare", options=group_companies["company_id"].tolist()
        )

        # Plotly Radar Chart (8 metrics)
        # Fetch ratios for group companies
        ratios_all = get_ratios(year=2024)
        group_ratios = ratios_all[
            ratios_all["company_id"].isin(group_companies["company_id"])
        ]

        metrics_8 = [
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "net_profit_margin_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "pat_cagr_5yr",
            "revenue_cagr_5yr",
            "composite_quality_score",
        ]
        metric_labels = [
            "ROE",
            "ROCE",
            "NPM",
            "D/E",
            "FCF Score",
            "PAT CAGR 5y",
            "Rev CAGR 5y",
            "Composite",
        ]

        # Compute percentile/scaled scores (0 to 100) for radar plot
        scaled_df = group_ratios.copy()
        for m in metrics_8:
            if m in scaled_df.columns:
                # Simple MinMax scaling within group for chart rendering
                min_v = scaled_df[m].min()
                max_v = scaled_df[m].max()
                if max_v > min_v:
                    scaled_df[m + "_norm"] = (
                        (scaled_df[m] - min_v) / (max_v - min_v)
                    ) * 100
                else:
                    scaled_df[m + "_norm"] = 50.0

        focus_row = scaled_df[scaled_df["company_id"] == focus_ticker]

        if not focus_row.empty:
            focus_vals = [focus_row[m + "_norm"].values[0] for m in metrics_8] + [
                focus_row[metrics_8[0] + "_norm"].values[0]
            ]
            avg_vals = [scaled_df[m + "_norm"].mean() for m in metrics_8] + [
                scaled_df[metrics_8[0] + "_norm"].mean()
            ]

            categories = metric_labels + [metric_labels[0]]

            fig_radar = go.Figure()
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=focus_vals,
                    theta=categories,
                    fill="toself",
                    name=focus_ticker,
                    line_color="#00b8d9",
                    fillcolor="rgba(0, 184, 217, 0.4)",
                )
            )
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=avg_vals,
                    theta=categories,
                    name=f"{selected_group} Avg",
                    line=dict(color="#ff5630", dash="dash"),
                )
            )
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                height=450,
                margin=dict(t=40, b=40, l=40, r=40),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with col_right:
        st.subheader("📋 Group Comparison Matrix")
        # Display side-by-side KPI table
        show_cols = [
            "company_id",
            "company_name",
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "net_profit_margin_pct",
            "debt_to_equity",
            "revenue_cagr_5yr",
            "composite_quality_score",
        ]
        table_df = group_ratios[show_cols].copy()
        table_df = table_df.merge(
            group_companies[["company_id", "is_benchmark"]], on="company_id"
        )

        def highlight_benchmark(row):
            if row.get("is_benchmark") == 1:
                return ["background-color: #fff3cd; font-weight: bold"] * len(row)
            return [""] * len(row)

        table_df.columns = [
            "Ticker",
            "Company Name",
            "ROE (%)",
            "ROCE (%)",
            "NPM (%)",
            "D/E",
            "Rev CAGR 5y (%)",
            "Composite",
            "is_benchmark",
        ]

        styled_df = table_df.style.apply(highlight_benchmark, axis=1).format(
            {
                "ROE (%)": "{:.2f}",
                "ROCE (%)": "{:.2f}",
                "NPM (%)": "{:.2f}",
                "D/E": "{:.2f}",
                "Rev CAGR 5y (%)": "{:.2f}",
                "Composite": "{:.2f}",
            }
        )

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.caption(
            "💡 Gold highlighted row indicates the Peer Group Benchmark company."
        )
