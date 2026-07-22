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
    page_title="Annual Reports — Nifty 100", page_icon="📑", layout="wide"
)

st.title("📑 Annual Reports & Document Repository")

companies_df = get_companies()
options = [f"{r['company_name']} ({r['id']})" for _, r in companies_df.iterrows()]
company_map = {
    f"{r['company_name']} ({r['id']})": r["id"] for _, r in companies_df.iterrows()
}

selected_company = st.selectbox("Select Company", options=options, index=0)
ticker = company_map[selected_company]

st.subheader(f"📄 Available Annual Reports for {selected_company}")

docs_df = get_documents(ticker)

if docs_df.empty:
    st.info("No annual report links stored for this company.")
else:
    for idx, row in docs_df.iterrows():
        yr = row.get("year")
        url = str(row.get("annual_report", "")).strip()

        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(f"**Financial Year {yr}**")

        with col2:
            if not url or url.lower() in ["nan", "none", "", "null"]:
                st.error("❌ Report unavailable")
            else:
                # Check if valid URL or test 404
                is_valid = True
                if url.startswith("http"):
                    try:
                        # Quick head check timeout 1s
                        resp = requests.head(
                            url, timeout=1.5, allow_redirects=True
                        )
                        if resp.status_code >= 400:
                            is_valid = False
                    except Exception:
                        is_valid = True  # don't block display if offline

                if is_valid:
                    st.markdown(f"[📥 Open Annual Report FY{yr} (BSE PDF)]({url})")
                else:
                    st.error("❌ Report unavailable (HTTP 404 Link Broken)")
        st.markdown("---")
