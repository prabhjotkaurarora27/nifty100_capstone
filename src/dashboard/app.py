import sys
from pathlib import Path
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 Nifty 100 Financial Analytics Dashboard")
st.markdown(
    """
    Welcome to the **Nifty 100 Financial Analytics & Peer Screener Dashboard**.
    
    Use the sidebar to navigate through the 8 analytics screens:
    
    1. 📊 **Home Dashboard**: Top KPIs, sector breakdown, and quality compounders.
    2. 🏢 **Company Profile**: Detailed financial cards, 10-year growth charts, and pros/cons analysis.
    3. 🔍 **Financial Screener**: Preset quality screens, 10 dynamic filter sliders, and CSV exports.
    4. 🥊 **Peer Comparison**: Radar chart visualizer vs peer group averages and benchmark matrix.
    5. 📉 **Financial Trends**: 10-year multi-metric YoY overlay charts with growth annotations.
    6. 🌐 **Sector Analytics**: Sector bubble charts (Revenue vs ROE vs MCap) and sector median comparisons.
    7. 🧱 **Capital Allocation**: Interactive treemap of all 92 companies grouped by allocation patterns.
    8. 📑 **Annual Reports**: Access company BSE annual report archives.
"""
)

# Render navigation buttons in main area / sidebar if running app directly
st.sidebar.title("Navigation")
pages = {
    "01 Home": "pages/01_home.py",
    "02 Profile": "pages/02_profile.py",
    "03 Screener": "pages/03_screener.py",
    "04 Peer Comparison": "pages/04_peers.py",
    "05 Trends": "pages/05_trends.py",
    "06 Sector Analytics": "pages/06_sectors.py",
    "07 Capital Allocation": "pages/07_capital.py",
    "08 Reports": "pages/08_reports.py",
}

for title, path in pages.items():
    if st.sidebar.button(title, use_container_width=True):
        try:
            st.switch_page(path)
        except Exception:
            pass
