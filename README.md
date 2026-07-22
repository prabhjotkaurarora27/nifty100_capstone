# Nifty 100 Financial Data Pipeline & Analytics Dashboard

> **Production-Grade Capstone Project** — End-to-End Financial Data Engineering, Quality Screening, Valuation Analytics & 8-Screen Interactive Streamlit Dashboard for 92 Nifty 100 Companies.

---

## 🚀 Quickstart & Dashboard Launch

```bash
# 1. Clone and enter project
git clone <your-repo-url>
cd nifty100_capstone

# 2. Create venv and activate
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Launch 8-Screen Interactive Streamlit Dashboard
streamlit run src/dashboard/app.py
```
> The dashboard will open automatically in your browser at `http://localhost:8501`.

---

## 📊 Dashboard Architecture & 8 Interactive Screens

The Streamlit dashboard (`src/dashboard/app.py`) features a wide-layout interface, sidebar navigation, `@st.cache_data(ttl=600)` caching, and 8 dedicated analytics pages:

| Page | Screen | Primary Features & Analytics |
| :--- | :--- | :--- |
| **01** | **📊 Home Dashboard** | 6 KPI tiles (Avg ROE, Median P/E, Median D/E, Total Companies, Median Rev CAGR, Debt-Free Count), 11-sector Plotly donut chart, Top 5 Quality Compounders table, Financial year selector (2019–2024). |
| **02** | **🏢 Company Profile** | Search by name/ticker, corporate metadata card, 6 latest KPI metrics, Plotly 10-year Revenue & Net Profit bar chart, ROE/ROCE dual-axis line chart, Green ✅ Pros & Red ❌ Cons badges. |
| **03** | **🔍 Financial Screener** | 10 metric sliders in sidebar, 6 preset filter buttons (Quality, Value, Growth, Dividend, Debt-Free, Turnaround), live result count, interactive DataFrame, CSV export download button. |
| **04** | **🥊 Peer Comparison** | 11 peer group selector, 8-axis Plotly `Scatterpolar` radar chart comparing target company vs peer group average, side-by-side KPI matrix with Gold benchmark row highlight. |
| **05** | **📉 Financial Trends** | Company selector + multi-metric overlay selector (up to 3 metrics), 10-year line chart with YoY % growth labels on data points, raw ratios historical table. |
| **06** | **🌐 Sector Analytics** | Sector dropdown, Plotly bubble chart (X = Revenue, Y = ROE, Size = Market Cap, Color = Sub-sector), sector median KPI comparison bar chart. |
| **07** | **🧱 Capital Allocation** | Plotly Treemap of all 92 companies grouped by 8 capital allocation archetypes (Reinvestor, Shareholder Returns, etc.), interactive drill-down company lists. |
| **08** | **📑 Annual Reports** | Company selector, list of available annual report financial years, clickable BSE PDF report links, Red "Report unavailable" 404 error badges. |

---

## 💡 Valuation Module (`src/analytics/valuation.py`)

Run the automated valuation engine to compute FCF Yield, 5-year Median P/E, Sector Median P/E, and Overvaluation Flags:

```bash
python src/analytics/valuation.py
```

- **Output Reports**:
  - `output/valuation_summary.xlsx` — 92 rows styled Excel report with conditional flag coloring.
  - `output/valuation_flags.csv` — Target list of Caution ($P/E > 1.5\times \text{Sector Median}$) and Discount ($P/E < 0.7\times \text{Sector Median}$) companies.

---

## 🧪 Testing & Quality Assurance

Run the comprehensive unit test suite across all 4 sprints (199 total tests):

```bash
PYTHONPATH=. venv/bin/pytest tests/ -v
```

- **Sprint 1 (ETL)**: 101 tests
- **Sprint 2 (KPIs)**: 20 tests
- **Sprint 3 (Screener & Peer)**: 14 tests
- **Sprint 4 (Dashboard & Valuation)**: 12 tests

---

## 📁 Repository Structure

```
nifty100_capstone/
├── config.py                   # Central config
├── config/
│   └── screener_config.yaml    # Screener thresholds config
├── db/
│   ├── schema.sql              # Database schema
│   └── nifty100.db             # SQLite Database (92 companies)
├── output/                     # Excel & CSV generated outputs
│   ├── screener_output.xlsx
│   ├── peer_comparison.xlsx
│   ├── valuation_summary.xlsx
│   └── valuation_flags.csv
├── pages/                      # 8 Streamlit Screen Files
│   ├── 01_home.py
│   ├── 02_profile.py
│   ├── 03_screener.py
│   ├── 04_peers.py
│   ├── 05_trends.py
│   ├── 06_sectors.py
│   ├── 07_capital.py
│   └── 08_reports.py
├── reports/
│   ├── radar_charts/           # 91 polar radar chart PNGs
│   ├── sprint1_review.md
│   ├── sprint2_retrospective.md
│   ├── sprint3_retrospective.md
│   └── sprint4_retrospective.md
├── src/
│   ├── etl/                    # Sprint 1 ETL Pipeline
│   ├── analytics/              # Sprint 2 & 3 Analytics Engines & Valuation
│   ├── screener/               # Sprint 3 Quality Screener Engine
│   └── dashboard/              # Sprint 4 Dashboard Scaffold & Caching
│       ├── app.py              # Streamlit Main App Entrypoint
│       └── utils/db.py         # Cached SQLite queries (@st.cache_data)
└── tests/                      # 199 Unit Tests
    ├── etl/
    ├── kpi/
    ├── screener/
    └── dashboard/
```
