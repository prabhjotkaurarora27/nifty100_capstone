import sys
from pathlib import Path
import pandas as pd
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_companies, get_documents

st.set_page_config(
    page_title="Annual Reports & Tearsheets — Nifty 100",
    page_icon="📑",
    layout="wide",
)

st.title("📑 Annual Reports & PDF Tearsheet Repository")

companies_df = get_companies()
options = [f"{r['company_name']} ({r['id']})" for _, r in companies_df.iterrows()]
company_map = {
    f"{r['company_name']} ({r['id']})": r["id"] for _, r in companies_df.iterrows()
}

selected_company = st.selectbox("Select Company", options=options, index=0)
ticker = company_map[selected_company]

st.markdown("---")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader(f"📄 Sprint 5 Executive Tearsheet ({ticker})")
    tearsheet_path = (
        PROJECT_ROOT / "reports" / "tearsheets" / f"{ticker}_tearsheet.pdf"
    )

    if tearsheet_path.exists():
        with open(tearsheet_path, "rb") as f:
            pdf_bytes = f.read()

        st.success(
            f"✅ 2-Page Executive Tearsheet available ({len(pdf_bytes)/1024:.1f} KB)"
        )
        st.download_button(
            label=f"📥 Download {ticker} Executive Tearsheet (PDF)",
            data=pdf_bytes,
            file_name=f"{ticker}_tearsheet.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Executive tearsheet PDF not found in repository.")

with col_right:
    portfolio_pdf = (
        PROJECT_ROOT / "reports" / "portfolio" / "portfolio_summary.pdf"
    )
    st.subheader("📚 Nifty 100 Portfolio Summary PDF")
    if portfolio_pdf.exists():
        with open(portfolio_pdf, "rb") as f:
            port_bytes = f.read()
        st.download_button(
            label="📥 Download Full Nifty 100 Portfolio Summary (92 Pages PDF)",
            data=port_bytes,
            file_name="portfolio_summary.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Portfolio summary PDF not found.")

st.markdown("---")
st.subheader(f"🔗 BSE Annual Report Archives for {selected_company}")

docs_df = get_documents(ticker)

if docs_df.empty:
    st.info("No annual report links stored in database for this company.")
else:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    for idx, row in docs_df.iterrows():
        yr = row.get("year")
        url = str(row.get("annual_report", "")).strip()

        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(f"### Financial Year {yr}")

        with col2:
            if not url or url.lower() in ["nan", "none", "", "null"]:
                st.error("❌ Report link unavailable in BSE registry")
            else:
                # Provide direct link to open in browser
                st.markdown(
                    f"🔗 [**Open FY{yr} Annual Report (BSE PDF Direct Link)**]({url})"
                )

        st.markdown("---")
